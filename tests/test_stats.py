import math

import pytest

from okey.stats import mean_and_se, median, paired_difference, wilson_interval


def test_wilson_known_values():
    lo, hi = wilson_interval(5, 10)
    assert lo == pytest.approx(0.2366, abs=1e-4)
    assert hi == pytest.approx(0.7634, abs=1e-4)
    lo, hi = wilson_interval(0, 10)
    assert lo == 0.0
    assert hi == pytest.approx(0.2775, abs=1e-4)
    lo, hi = wilson_interval(10, 10)
    assert hi == pytest.approx(1.0)
    assert lo == pytest.approx(0.7225, abs=1e-4)
    assert wilson_interval(0, 0) == (0.0, 1.0)


def test_wilson_shrinks_with_n():
    w1 = wilson_interval(20, 100)
    w2 = wilson_interval(200, 1000)
    assert (w2[1] - w2[0]) < (w1[1] - w1[0])


@pytest.mark.parametrize(("s", "n"), [(-1, 10), (11, 10), (0, -1)])
def test_wilson_invalid(s, n):
    with pytest.raises(ValueError):
        wilson_interval(s, n)


def test_mean_and_se():
    mean, se = mean_and_se([1, 2, 3, 4])
    assert mean == 2.5
    assert se == pytest.approx(math.sqrt((2.25 + 0.25 + 0.25 + 2.25) / 3 / 4))
    assert mean_and_se([7]) == (7, 0.0)
    with pytest.raises(ValueError):
        mean_and_se([])


def test_paired_difference():
    diff, se = paired_difference([10, 20, 30], [10, 10, 10])
    assert diff == 10
    assert se == pytest.approx(math.sqrt(100 / 3))
    assert paired_difference([5, 5], [5, 5]) == (0, 0)
    with pytest.raises(ValueError):
        paired_difference([1], [1, 2])


def test_median():
    assert median([3, 1, 2]) == 2
    assert median([4, 1, 2, 3]) == 2.5
    with pytest.raises(ValueError):
        median([])
