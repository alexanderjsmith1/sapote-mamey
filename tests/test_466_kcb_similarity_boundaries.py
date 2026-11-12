"""Percent similarity bands include their stated lower boundary."""
import math
import pytest
from mamey.precision import similarity_band

@pytest.mark.parametrize('value,expected', [
    (70.0, 'high'),
    (math.nextafter(70.0, -math.inf), 'moderate'),
    (40.0, 'moderate'),
    (math.nextafter(40.0, -math.inf), 'low'),
])
def test_similarity_band_boundary(value, expected):
    assert similarity_band(value) == expected
