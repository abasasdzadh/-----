from abc import ABC, abstractmethod
from pathlib import Path
from typing import List, Dict, Any

class TTSProvider(ABC):
    @abstractmethod
    async def generate_audio(
        self,
        text: str,
        voice_id: str,
        output_path: Path
    ) -> Path:
        """Synthesizes text into an audio file at output_path."""
        pass

    @abstractmethod
    async def get_available_voices(self, target_language: str = None) -> List[Dict[str, Any]]:
        """Returns the list of supported voices for the given language."""
        pass