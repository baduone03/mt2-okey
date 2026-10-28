"""Hızlı rollout motoru: yalnızca tamsayı maskeleri ve önceden hesaplanmış tablolar.

Monte Carlo değerlendirmesinde zamanın neredeyse tamamı "eylemden sonra oyunu
sonuna kadar oyna" adımında geçer. Bu modül aynı kuralları ve aynı politika
kararlarını nesne ve doğrulama yükü olmadan uygular. Doğruluğu, `state.apply` +
politika sınıflarını kullanan referans yolla birebir karşılaştırılarak test edilir
(tests/test_fast.py).
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from functools import lru_cache

from okey.cards import ALL_CARDS
from okey.combos import ALL_COMBOS, COMBOS_BY_CARD
from okey.rules import RuleConfig


@dataclass(frozen=True)
class Tables:
    # (maske, puan); puana göre azalan, eşitlikte maskeye göre artan sıra. İlk uyan üçlü,
    # GreedyPolicy.best_play ile aynı seçimdir: max(puan, -maske).
    combos: tuple[tuple[int, int], ...]
    # card_combos[i]: i indeksli kartı içeren ve puanı >= min_points olan (maske, puan) çiftleri
    # (atma potansiyeli hesabı için).
    card_combos: tuple[tuple[tuple[int, int], ...], ...]
    # Atma eşitliğinde (numara, renk) sırası; least_useful_card ile aynı.
    card_rank: tuple[int, ...]
    hand_size: int


@lru_cache(maxsize=32)
def tables(rules: RuleConfig, min_points: int = 0) -> Tables:
    combos = sorted(((c.mask, c.points(rules)) for c in ALL_COMBOS), key=lambda mp: (-mp[1], mp[0]))
    card_combos = tuple(
        tuple(
            (c.mask, c.points(rules))
            for c in COMBOS_BY_CARD[card.index]
            if c.points(rules) >= min_points
        )
        for card in ALL_CARDS
    )
    order = sorted(ALL_CARDS, key=lambda c: (c.number, c.color))
    rank = [0] * len(ALL_CARDS)
    for r, card in enumerate(order):
        rank[card.index] = r
    return Tables(tuple(combos), card_combos, tuple(rank), rules.hand_size)


def best_combo(hand: int, t: Tables) -> tuple[int, int] | None:
    for mask, points in t.combos:
        if mask & hand == mask:
            return mask, points
    return None


def least_useful(hand: int, available: int, t: Tables) -> int:
    """Masadaki kartlardan, hâlâ kurulabilir üçlülerinin toplam puanı en düşük olanın biti."""
    best_key = None
    best_bit = 0
    rest = hand
    while rest:
        bit = rest & -rest
        rest ^= bit
        idx = bit.bit_length() - 1
        potential = 0
        for mask, points in t.card_combos[idx]:
            if mask & available == mask:
                potential += points
        key = (potential, t.card_rank[idx])
        if best_key is None or key < best_key:
            best_key, best_bit = key, bit
    return best_bit


def rollout(
    hand: int,
    score: int,
    order: Sequence[int],
    t: Tables,
    min_points: int = 0,
    discard_requires_no_combo: bool = False,
) -> int:
    """Seçici politika ile oyunu sonuna kadar oynar ve oyun sonu puanını döndürür.

    En iyi üçlü `min_points` veya üstündeyse (ya da deste bittiyse, ya da kurallar üçlü
    varken atmaya izin vermiyorsa) oynanır; aksi halde en az işe yarayan kart atılır.
    `min_points = 0` açgözlü politikadır. `order`: görülmemiş kartların bitleri,
    çekilme sırasıyla. `t`, aynı `min_points` ile üretilmiş tablolar olmalıdır.
    """
    rest = 0
    for bit in order:
        rest |= bit
    i, n = 0, len(order)
    hand_size = t.hand_size
    while True:
        while i < n and hand.bit_count() < hand_size:
            bit = order[i]
            hand |= bit
            rest &= ~bit
            i += 1
        combo = best_combo(hand, t)
        if combo is not None and (combo[1] >= min_points or i >= n or discard_requires_no_combo):
            hand &= ~combo[0]
            score += combo[1]
        elif i < n:
            hand &= ~least_useful(hand, hand | rest, t)
        else:
            return score


def greedy_rollout(hand: int, score: int, order: Sequence[int], t: Tables) -> int:
    """Açgözlü politika ile oyunu sonuna kadar oynar (eşiksiz seçici politika)."""
    return rollout(hand, score, order, t)


def order_bits(order: Sequence) -> tuple[int, ...]:
    return tuple(card.bit for card in order)
