import json
import httpx
from typing import List
from app.core.config import get_effective_gemini_key, settings
from app.models.transcript import TranscriptSegment, TranslationSegment, TranslationData
from app.utils.logger import logger

class TranslationService:
    GEMINI_API_URL = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"

    @classmethod
    async def translate_transcript(
        cls,
        segments: List[TranscriptSegment],
        source_lang: str,
        target_lang: str,
        batch_size: int = 40
    ) -> TranslationData:
        api_key = get_effective_gemini_key()
        if not api_key:
            raise ValueError(
                "کلید Gemini API Key تنظیم نشده است. لطفاً آن را در فایل .env یا بخش تنظیمات وب‌سایت وارد کنید."
            )

        translated_segments: List[TranslationSegment] = []
        
        # Batch segments to keep conversational context and save token requests
        for i in range(0, len(segments), batch_size):
            batch = segments[i:i + batch_size]
            batch_result = await cls._translate_batch(batch, source_lang, target_lang, api_key)
            translated_segments.extend(batch_result)

        return TranslationData(
            source_language=source_lang,
            target_language=target_lang,
            segments=translated_segments
        )

    @classmethod
    async def _translate_batch(
        cls,
        batch: List[TranscriptSegment],
        source_lang: str,
        target_lang: str,
        api_key: str
    ) -> List[TranslationSegment]:
        url = cls.GEMINI_API_URL.format(model=settings.GEMINI_MODEL) + f"?key={api_key}"
        
        # System instructions crafted for high-quality audio dubbing
        system_instruction = (
            "You are an expert dubbing translator and script adapter. "
            f"Translate the following spoken video segments from '{source_lang}' to '{target_lang}'.\n"
            "CRITICAL RULES:\n"
            "1. Produce natural, conversational spoken dialogue suitable for voiceover/dubbing.\n"
            "2. Keep the phrasing concise so it fits within the original speaking duration.\n"
            "3. Retain proper nouns and contextual nuance accurately.\n"
            "4. You MUST respond with ONLY a valid JSON array containing objects with exact keys 'id' and 'translation'.\n"
            "5. Do NOT include markdown code fences, comments, or explanations outside the JSON."
        )

        input_payload = [{"id": s.id, "text": s.text} for s in batch]
        
        prompt_text = (
            f"{system_instruction}\n\n"
            f"Input Segments:\n{json.dumps(input_payload, ensure_ascii=False)}"
        )

        body = {
            "contents": [
                {
                    "parts": [{"text": prompt_text}]
                }
            ],
            "generationConfig": {
                "temperature": 0.2,
                "response_mime_type": "application/json"
            }
        }

        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(url, json=body)
            if response.status_code != 200:
                logger.error(f"Gemini API Error: {response.text}")
                raise RuntimeError(f"خطای Gemini API ({response.status_code}): {response.text}")

            resp_json = response.json()
            try:
                raw_text = resp_json["candidates"][0]["content"]["parts"][0]["text"]
                parsed_translations = json.loads(raw_text)
            except (KeyError, IndexError, json.JSONDecodeError) as e:
                logger.error(f"Failed to parse Gemini translation response: {e}")
                raise RuntimeError("پاسخ دریافتی از هوش مصنوعی Gemini ساختار معتبر JSON نداشت.")

        # Map back to TranslationSegment preserving timestamps
        trans_map = {item["id"]: item.get("translation", "") for item in parsed_translations if "id" in item}
        
        results: List[TranslationSegment] = []
        for s in batch:
            translated_txt = trans_map.get(s.id, s.text) # fallback to original if missing
            results.append(
                TranslationSegment(
                    id=s.id,
                    start=s.start,
                    end=s.end,
                    source_text=s.text,
                    translated_text=translated_txt
                )
            )
        return results