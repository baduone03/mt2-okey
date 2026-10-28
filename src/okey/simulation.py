"""Oyun oynatma ve ortak rastgele sayılar (common random numbers).

Gerçek oyunda kartlar desteden rastgele sırayla gelir; simülasyon bu sırayı
görülmemiş kartların bir permütasyonu olarak temsil eder. Farklı aday hamleler
veya stratejiler aynı permütasyon listesiyle değerlendirilir; böylece aralarındaki
fark kart şansından değil, kararlardan kaynaklanır.
"""

from __future__ import annotations

import random
from collections.abc import Sequence

from okey.cards import ALL_CARDS, Card, cards_of, mask_of
from okey.rules import RuleConfig
from okey.state import Action, Draw, GameState, Phase, apply
from okey.strategies.base import Policy

# Bir oyunda en fazla 24 çekme + 24 karar olabilir; döngü koruması.
_MAX_STEPS = 2 * len(ALL_CARDS) + 1


def _sub_seed(seed: int, index: int) -> int:
    return (seed * 1_000_003 + index) & 0xFFFF_FFFF_FFFF


def deck_order(unseen: int, seed: int, index: int) -> tuple[Card, ...]:
    """`deck_orders(unseen, n, seed)[index]` ile aynı permütasyonu tek başına üretir."""
    order = list(cards_of(unseen))
    random.Random(_sub_seed(seed, index)).shuffle(order)
    return tuple(order)


def deck_orders(unseen: int, n: int, seed: int) -> list[tuple[Card, ...]]:
    """Görülmemiş kartların n adet tekrarlanabilir rastgele permütasyonu."""
    if n < 0:
        raise ValueError(f"Permütasyon sayısı negatif olamaz: {n}")
    return [deck_order(unseen, seed, i) for i in range(n)]


def policy_rng(seed: int, index: int) -> random.Random:
    """i'inci simülasyonun politika rastgeleliği; desteden bağımsız ama tekrarlanabilir."""
    return random.Random(_sub_seed(seed, index) ^ 0x5DEECE66D)


def play_out(
    state: GameState,
    rules: RuleConfig,
    policy: Policy,
    deck_order: Sequence[Card],
    rng: random.Random,
) -> GameState:
    """Durumdan başlayarak oyunu sonuna kadar oynar.

    `deck_order`, görülmemiş kartların tamamı olmalıdır ve kartlar bu sırayla çekilir.
    """
    if len(deck_order) != state.deck_remaining or mask_of(deck_order) != state.unseen:
        raise ValueError("Deste sırası, görülmemiş kartların bir permütasyonu olmalı.")
    next_card = 0
    for _ in range(_MAX_STEPS):
        phase = state.phase(rules)
        if phase is Phase.FINISHED:
            return state
        action: Action
        if phase is Phase.AWAITING_DRAW:
            action = Draw(deck_order[next_card])
            next_card += 1
        else:
            action = policy.choose(state, rules, rng)
        state = apply(state, action, rules)
    raise RuntimeError("Oyun beklenen adım sayısında bitmedi (kural yapılandırmasını kontrol edin).")


def play_after(
    state: GameState,
    action: Action,
    rules: RuleConfig,
    policy: Policy,
    deck_order: Sequence[Card],
    rng: random.Random,
) -> GameState:
    """Önce verilen eylemi uygular, sonra oyunu politika ile sonuna kadar oynar."""
    return play_out(apply(state, action, rules), rules, policy, deck_order, rng)
