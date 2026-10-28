"""Simülasyon sonuçları için küçük istatistik yardımcıları (saf Python)."""

from __future__ import annotations

import math
from collections.abc import Sequence

Z_95 = 1.959963984540054


def wilson_interval(successes: int, n: int, z: float = Z_95) -> tuple[float, float]:
    """Binom oranı için Wilson güven aralığı; n = 0 ise (0, 1)."""
    if n < 0 or not 0 <= successes <= n:
        raise ValueError(f"Geçersiz sayılar: başarı={successes}, n={n}")
    if n == 0:
        return 0.0, 1.0
    p = successes / n
    denom = 1 + z * z / n
    center = (p + z * z / (2 * n)) / denom
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / denom
    return max(0.0, center - half), min(1.0, center + half)


def mean_and_se(values: Sequence[float]) -> tuple[float, float]:
    """Ortalama ve ortalamanın standart hatası (n < 2 ise hata 0)."""
    n = len(values)
    if n == 0:
        raise ValueError("Boş örneklem")
    mean = sum(values) / n
    if n < 2:
        return mean, 0.0
    var = sum((v - mean) ** 2 for v in values) / (n - 1)
    return mean, math.sqrt(var / n)


def paired_difference(a: Sequence[float], b: Sequence[float]) -> tuple[float, float]:
    """Eşleştirilmiş örneklerde (aynı deste sıraları) ortalama fark ve standart hatası."""
    if len(a) != len(b):
        raise ValueError("Eşleştirilmiş örneklemler aynı uzunlukta olmalı")
    return mean_and_se([x - y for x, y in zip(a, b)])


def median(values: Sequence[float]) -> float:
    if not values:
        raise ValueError("Boş örneklem")
    s = sorted(values)
    mid = len(s) // 2
    return float(s[mid]) if len(s) % 2 else (s[mid - 1] + s[mid]) / 2
