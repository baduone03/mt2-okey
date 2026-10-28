"""Yapılandırılabilir oyun kuralları ve sandık sınıfları.

Değerlerin kaynağı ve doğrulama durumu için bkz. docs/RULES.md.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum

from okey.cards import NUMBERS

RUN_LENGTH = 3
RUN_STARTS: tuple[int, ...] = tuple(NUMBERS[: len(NUMBERS) - RUN_LENGTH + 1])  # 1..6


class Chest(Enum):
    BRONZE = "bronz"
    SILVER = "gümüş"
    GOLD = "altın"


class RefillPolicy(Enum):
    # Oynanan/atılan kartların yerine masa desteden hemen tamamlanır (docs/RULES.md A5).
    IMMEDIATE = "immediate"


@dataclass(frozen=True)
class ChestThresholds:
    silver: int = 300
    gold: int = 400

    def __post_init__(self) -> None:
        if not 0 < self.silver < self.gold:
            raise ValueError(
                f"Eşikler 0 < gümüş < altın olmalı, gelen: gümüş={self.silver}, altın={self.gold}"
            )


@dataclass(frozen=True)
class RuleConfig:
    """Bir sunucu/etkinlik sürümünün kuralları.

    Puan tabloları formül değil veri olarak tutulur:
    - same_number_points[n-1]: n-n-n üçlüsü (n = 1..8)
    - same_color_run_points[s-1]: aynı renk s, s+1, s+2 serisi (s = 1..6)
    - mixed_run_points[s-1]: karışık renk s, s+1, s+2 serisi (s = 1..6)
    """

    name: str
    same_number_points: tuple[int, ...]
    same_color_run_points: tuple[int, ...]
    mixed_run_points: tuple[int, ...]
    hand_size: int = 5
    chest_thresholds: ChestThresholds = field(default_factory=ChestThresholds)
    # docs/RULES.md A6: masada geçerli üçlü varken kart atmak yasak mı?
    discard_requires_no_combo: bool = False
    refill_policy: RefillPolicy = RefillPolicy.IMMEDIATE

    def __post_init__(self) -> None:
        _check_table("same_number_points", self.same_number_points, len(NUMBERS))
        _check_table("same_color_run_points", self.same_color_run_points, len(RUN_STARTS))
        _check_table("mixed_run_points", self.mixed_run_points, len(RUN_STARTS))
        if self.hand_size < RUN_LENGTH:
            raise ValueError(f"Masa boyutu en az {RUN_LENGTH} olmalı, gelen: {self.hand_size}")

    def chest_for(self, score: int) -> Chest:
        if score < 0:
            raise ValueError(f"Puan negatif olamaz: {score}")
        if score >= self.chest_thresholds.gold:
            return Chest.GOLD
        if score >= self.chest_thresholds.silver:
            return Chest.SILVER
        return Chest.BRONZE


def _check_table(name: str, table: tuple[int, ...], expected_len: int) -> None:
    if len(table) != expected_len:
        raise ValueError(f"{name} {expected_len} değer içermeli, gelen: {len(table)}")
    if any(not isinstance(v, int) or v < 0 for v in table):
        raise ValueError(f"{name} negatif olmayan tamsayılardan oluşmalı: {table}")


OFFICIAL_2026 = RuleConfig(
    name="Resmî (2026)",
    same_number_points=(20, 30, 40, 50, 60, 70, 80, 90),
    same_color_run_points=(50, 60, 70, 80, 90, 100),
    mixed_run_points=(10, 20, 30, 40, 50, 60),
)

PRESETS: dict[str, RuleConfig] = {"official_2026": OFFICIAL_2026}

# Kaynaklardan kesinleştirilemeyen kurallar; arayüz bunları kullanıcıya gösterir.
UNVERIFIED_RULES: dict[str, str] = {
    "discard_requires_no_combo": "Masada geçerli üçlü varken kart atılabilir mi? (RULES.md A6)",
    "refill_policy": "Oynanan kartların yerine masa hemen 5'e tamamlanıyor mu? (RULES.md A5)",
    "same_number_points": "Ara değerler (+10 adım) resmî tablodan satır satır doğrulanmadı.",
    "same_color_run_points": "Ara değerler (+10 adım) resmî tablodan satır satır doğrulanmadı.",
    "mixed_run_points": "Ara değerler (+10 adım) resmî tablodan satır satır doğrulanmadı.",
}
