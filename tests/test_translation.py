import json
import pytest
from app.models.transcript import TranscriptSegment

def test_gemini_translation_payload_alignment():
    segments = [
        TranscriptSegment(id=1, start=0.0, end=3.0, text="Hello world"),
        TranscriptSegment(id=2, start=3.1, end=5.5, text="How are you?")
    ]
    mock_gemini_response = [
        {"id": 1, "translation": "سلام دنیا"},
        {"id": 2, "translation": "حالت چطوره؟"}
    ]
    
    trans_map = {item["id"]: item["translation"] for item in mock_gemini_response}
    assert trans_map[1] == "سلام دنیا"
    assert trans_map[2] == "حالت چطوره؟"