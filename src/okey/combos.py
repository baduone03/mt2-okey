"""Geçerli üçlülerin tespiti ve puanlanması.

Tüm geçerli üçlüler (170 adet) içe aktarma sırasında 24 kartın bütün 3'lü alt kümeleri
`classify` ile taranarak bir kez üretilir.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from enum import Enum
from itertools import combinations

from okey.cards import ALL_CARDS, Card, mask_of
from okey.rules import RUN_LENGTH, RuleConfig

COMBO_SIZE = RUN_LENGTH


class ComboKind(Enum):
    SAME_NUMBER = "aynı numara"
    SAME_COLOR_RUN = "aynı renk seri"
    MIXED_RUN = "karışık renk seri"


class InvalidComboError(ValueError):
    """Verilen kartlar geçerli bir üçlü oluşturmuyor."""


@dataclass(frozen=True)
class Combo:
    kind: ComboKind
    cards: tuple[Card, Card, Card]  # numaraya, sonra renge göre sıralı
    mask: int

    @property
    def low(self) -> int:
        """Puan tablosundaki satır: aynı numarada n, seride başlangıç numarası."""
        return self.cards[0].number

    def points(self, rules: RuleConfig) -> int:
        if self.kind is ComboKind.SAME_NUMBER:
            return rules.same_number_points[self.low - 1]
        if self.kind is ComboKind.SAME_COLOR_RUN:
            return rules.same_color_run_points[self.low - 1]
        return rules.mixed_run_points[self.low - 1]

    def __str__(self) -> str:
        return "-".join(card.code for card in self.cards)


def _sorted_cards(cards: Iterable[Card]) -> tuple[Card, ...]:
    cards = tuple(cards)
    if len(cards) != COMBO_SIZE:
        raise InvalidComboError(f"Üçlü tam {COMBO_SIZE} kart içermeli, gelen: {len(cards)}")
    if len(set(cards)) != COMBO_SIZE:
        raise InvalidComboError(f"Aynı kart bir üçlüde iki kez kullanılamaz: {[str(c) for c in cards]}")
    return tuple(sorted(cards, key=lambda c: (c.number, c.color)))


def classify(cards: Iterable[Card]) -> ComboKind | None:
    """Üç farklı kartın oluşturduğu kombinasyon türünü, geçersizse None döndürür.

    Kart sayısı 3 değilse veya aynı kart tekrar ediyorsa InvalidComboError verir.
    """
    a, b, c = _sorted_cards(cards)
    if a.number == b.number == c.number:
        # Her renk/numara tek kopya olduğundan farklı kartlar zaten farklı renktedir.
        return ComboKind.SAME_NUMBER if len({a.color, b.color, c.color}) == 3 else None
    if b.number == a.number + 1 and c.number == b.number + 1:
        return ComboKind.SAME_COLOR_RUN if a.color == b.color == c.color else ComboKind.MIXED_RUN
    return None


def make_combo(cards: Iterable[Card]) -> Combo:
    ordered = _sorted_cards(cards)
    kind = classify(ordered)
    if kind is None:
        raise InvalidComboError(f"Geçerli bir üçlü değil: {'-'.join(c.code for c in ordered)}")
    return Combo(kind=kind, cards=ordered, mask=mask_of(ordered))  # type: ignore[arg-type]


def score(cards: Iterable[Card], rules: RuleConfig) -> int:
    return make_combo(cards).points(rules)


ALL_COMBOS: tuple[Combo, ...] = tuple(
    make_combo(triple) for triple in combinations(ALL_CARDS, COMBO_SIZE) if classify(triple)
)


def combos_in(mask: int) -> list[Combo]:
    """Maskedeki kartlarla oluşturulabilen tüm geçerli üçlüler."""
    return [combo for combo in ALL_COMBOS if combo.mask & mask == combo.mask]


# COMBOS_BY_CARD[i]: indeksi i olan kartı içeren tüm geçerli üçlüler.
COMBOS_BY_CARD: tuple[tuple[Combo, ...], ...] = tuple(
    tuple(combo for combo in ALL_COMBOS if combo.mask & card.bit) for card in ALL_CARDS
)
