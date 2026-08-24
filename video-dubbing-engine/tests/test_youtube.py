import pytest
from fastapi import HTTPException
from app.core.security import validate_youtube_url

def test_valid_youtube_urls():
    valid_cases = [
        "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
        "https://youtube.com/watch?v=dQw4w9WgXcQ",
        "https://youtu.be/dQw4w9WgXcQ",
        "https://www.youtube.com/shorts/dQw4w9WgXcQ",
        "http://www.youtube.com/watch?v=dQw4w9WgXcQ&t=10s"
    ]
    for url in valid_cases:
        assert validate_youtube_url(url) == url

def test_invalid_youtube_urls():
    invalid_cases = [
        "https://vimeo.com/123456",
        "not_a_url",
        "https://youtube.com/invalid_path",
        ""
    ]
    for url in invalid_cases:
        with pytest.raises(HTTPException):
            validate_youtube_url(url)