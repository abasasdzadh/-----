import pytest
from app.services.tts.factory import get_tts_provider
from app.services.tts.edge_tts_provider import EdgeTTSProvider

def test_tts_factory():
    provider = get_tts_provider("edge")
    assert isinstance(provider, EdgeTTSProvider)

@pytest.mark.asyncio
async def test_edge_tts_voice_filtering():
    provider = EdgeTTSProvider()
    voices = await provider.get_available_voices(target_language="fa")
    assert len(voices) > 0
    # Persian voices should contain fa in locale
    for v in voices:
        assert "fa" in v["locale"].lower()