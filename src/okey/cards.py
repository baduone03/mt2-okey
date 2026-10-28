"""Kart modeli: 3 renk x 8 numara = 24 tekil kart.

Her kart 0..23 arası bir indekse ve 24 bitlik bir maskedeki tek bir bite karşılık gelir.
Kart kümeleri tamsayı maskeleriyle temsil edilir; kullanıcıya dönük API `Card` nesneleriyle çalışır.
"""

from __future__ import annotations

import re
from collections.abc import Iterable
from dataclasses import dataclass
from enum import IntEnum

MIN_NUMBER = 1
MAX_NUMBER = 8
NUMBERS: tuple[int, ...] = tuple(range(MIN_NUMBER, MAX_NUMBER + 1))


class Color(IntEnum):
    RED = 0
    BLUE = 1
    YELLOW = 2

    @property
    def code(self) -> str:
        """Kısa Türkçe kod: K(ırmızı), M(avi), S(arı)."""
        return _COLOR_CODES[self]

    @property
    def label_tr(self) -> str:
        return _COLOR_LABELS_TR[self]


_COLOR_CODES = {Color.RED: "K", Color.BLUE: "M", Color.YELLOW: "S"}
_COLOR_LABELS_TR = {Color.RED: "Kırmızı", Color.BLUE: "Mavi", Color.YELLOW: "Sarı"}
# Türkçe (K/M/S) ve İngilizce (R/B/Y) baş harfleri kabul edilir; kümeler çakışmaz.
_CODE_TO_COLOR = {
    "K": Color.RED, "R": Color.RED,
    "M": Color.BLUE, "B": Color.BLUE,
    "S": Color.YELLOW, "Y": Color.YELLOW,
}


class CardParseError(ValueError):
    """Metin olarak girilen kart çözümlenemedi."""


@dataclass(frozen=True, order=True)
class Card:
    color: Color
    number: int

    def __post_init__(self) -> None:
        if not isinstance(self.color, Color):
            raise TypeError(f"Renk Color olmalı, gelen: {self.color!r}")
        if not isinstance(self.number, int) or not MIN_NUMBER <= self.number <= MAX_NUMBER:
            raise ValueError(
                f"Kart numarası {MIN_NUMBER}-{MAX_NUMBER} arasında olmalı, gelen: {self.number!r}"
            )

    @property
    def index(self) -> int:
        return int(self.color) * len(NUMBERS) + (self.number - MIN_NUMBER)

    @property
    def bit(self) -> int:
        return 1 << self.index

    @property
    def code(self) -> str:
        return f"{self.color.code}{self.number}"

    def __str__(self) -> str:
        return self.code


ALL_CARDS: tuple[Card, ...] = tuple(Card(color, number) for color in Color for number in NUMBERS)
FULL_MASK: int = (1 << len(ALL_CARDS)) - 1


def card_from_index(index: int) -> Card:
    if not 0 <= index < len(ALL_CARDS):
        raise ValueError(f"Kart indeksi 0-{len(ALL_CARDS) - 1} arasında olmalı, gelen: {index}")
    return ALL_CARDS[index]


def mask_of(cards: Iterable[Card]) -> int:
    """Kartları maskeye çevirir. Aynı kart iki kez verilirse hata verir."""
    mask = 0
    for card in cards:
        if mask & card.bit:
            raise ValueError(f"Aynı kart birden fazla kez verildi: {card}")
        mask |= card.bit
    return mask


def cards_of(mask: int) -> tuple[Card, ...]:
    """Maskedeki kartları indeks sırasıyla döndürür."""
    if mask & ~FULL_MASK or mask < 0:
        raise ValueError(f"Geçersiz kart maskesi: {mask:#x}")
    return tuple(card for card in ALL_CARDS if mask & card.bit)


_CARD_PATTERN = re.compile(r"^([A-Za-z])\s*([0-9]+)$")


def parse_card(text: str) -> Card:
    """'K5', 'm 3', 'Y8' gibi bir girişi karta çevirir."""
    match = _CARD_PATTERN.match(text.strip())
    if not match:
        raise CardParseError(f"Kart biçimi tanınmadı: {text!r} (örnek: K5, M3, S8)")
    letter, digits = match.groups()
    color = _CODE_TO_COLOR.get(letter.upper())
    if color is None:
        raise CardParseError(f"Bilinmeyen renk kodu {letter!r}: K/M/S (veya R/B/Y) kullanın")
    try:
        return Card(color, int(digits))
    except ValueError as exc:
        raise CardParseError(str(exc)) from exc


def parse_cards(text: str) -> tuple[Card, ...]:
    """Boşluk veya virgülle ayrılmış kartları çözer; tekrar eden kartı reddeder."""
    tokens = [token for token in re.split(r"[\s,;]+", text.strip()) if token]
    cards = tuple(parse_card(token) for token in tokens)
    seen: set[Card] = set()
    for card in cards:
        if card in seen:
            raise CardParseError(f"Aynı kart iki kez girildi: {card}")
        seen.add(card)
    return cards
