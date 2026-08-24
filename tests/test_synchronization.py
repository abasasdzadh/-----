import pytest
from app.core.config import settings

def test_speed_factor_clamping():
    # Test min bound clamp
    speed_factor = 0.5
    clamped = max(settings.MIN_SPEED_FACTOR, min(settings.MAX_SPEED_FACTOR, speed_factor))
    assert clamped == settings.MIN_SPEED_FACTOR

    # Test max bound clamp
    speed_factor = 2.5
    clamped = max(settings.MIN_SPEED_FACTOR, min(settings.MAX_SPEED_FACTOR, speed_factor))
    assert clamped == settings.MAX_SPEED_FACTOR

    # Test within bounds
    speed_factor = 1.15
    clamped = max(settings.MIN_SPEED_FACTOR, min(settings.MAX_SPEED_FACTOR, speed_factor))
    assert clamped == 1.15