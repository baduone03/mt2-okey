import random
from collections import Counter

import pytest

from okey.cards import ALL_CARDS, FULL_MASK, mask_of, parse_cards
from okey.rules import OFFICIAL_2026
from okey.simulation import deck_orders, play_after, play_out, policy_rng
from okey.state import Discard, GameState, Phase
from okey.strategies import GreedyPolicy, RandomPolicy

RULES = OFFICIAL_2026


def test_deck_orders_are_permutations_of_unseen():
    state = GameState(hand=mask_of(parse_cards("K1 K2 K3 M4 S5")), discarded=mask_of(parse_cards("S8")))
    orders = deck_orders(state.unseen, 50, seed=7)
    assert len(orders) == 50
    for order in orders:
        assert len(order) == 18
        assert len(set(order)) == 18
        assert mask_of(order) == state.unseen  # görülmüş kart yok, tekrar yok


def test_deck_orders_reproducible_and_seed_dependent():
    assert deck_orders(FULL_MASK, 5, seed=1) == deck_orders(FULL_MASK, 5, seed=1)
    assert deck_orders(FULL_MASK, 5, seed=1) != deck_orders(FULL_MASK, 5, seed=2)
    assert len(set(deck_orders(FULL_MASK, 100, seed=3))) == 100
    # İlk n permütasyon, n'den bağımsızdır (örneklem büyütmek önceki sonuçları değiştirmez).
    assert deck_orders(FULL_MASK, 10, seed=4)[:5] == deck_orders(FULL_MASK, 5, seed=4)


def test_deck_orders_first_card_roughly_uniform():
    orders = deck_orders(FULL_MASK, 24_000, seed=11)
    counts = Counter(order[0] for order in orders)
    assert set(counts) == set(ALL_CARDS)
    # Beklenen 1000; çok gevşek sınır (rastgele başarısızlık olasılığı ihmal edilebilir).
    assert all(800 < n < 1200 for n in counts.values())


def test_deck_orders_negative_rejected():
    with pytest.raises(ValueError):
        deck_orders(FULL_MASK, -1, seed=0)


@pytest.mark.parametrize("policy", [GreedyPolicy(), RandomPolicy()], ids=lambda p: p.name)
def test_play_out_full_game(policy):
    for i, order in enumerate(deck_orders(FULL_MASK, 100, seed=5)):
        final = play_out(GameState(), RULES, policy, order, policy_rng(5, i))
        assert final.phase(RULES) is Phase.FINISHED
        assert final.deck_remaining == 0
        assert final.score == sum(c.points(RULES) for c in final.played)
        assert final.hand.bit_count() + 3 * len(final.played) + final.discarded.bit_count() == 24


class SpyPolicy:
    """Açgözlü politikayı sarar ve her karar anında görülmüş kart maskesini kaydeder."""

    name = "Casus"

    def __init__(self):
        self.inner = GreedyPolicy()
        self.seen: list[int] = []

    def choose(self, state, rules, rng):
        self.seen.append(FULL_MASK & ~state.unseen)
        return self.inner.choose(state, rules, rng)


def test_play_out_draws_in_given_order():
    for order in deck_orders(FULL_MASK, 20, seed=9):
        spy = SpyPolicy()
        play_out(GameState(), RULES, spy, order, random.Random(0))
        assert spy.seen
        for seen in spy.seen:
            # Görülen kartlar her zaman deste sırasının bir ön ekidir.
            assert seen == mask_of(order[: seen.bit_count()])


def test_play_out_is_reproducible():
    order = deck_orders(FULL_MASK, 1, seed=13)[0]
    a = play_out(GameState(), RULES, RandomPolicy(), order, policy_rng(13, 0))
    b = play_out(GameState(), RULES, RandomPolicy(), order, policy_rng(13, 0))
    assert a == b


def test_play_out_rejects_wrong_deck():
    state = GameState(hand=mask_of(parse_cards("K1")))
    order = deck_orders(FULL_MASK, 1, seed=0)[0]  # K1'i de içeriyor
    with pytest.raises(ValueError, match="permütasyon"):
        play_out(state, RULES, GreedyPolicy(), order, random.Random(0))
    with pytest.raises(ValueError):
        play_out(state, RULES, GreedyPolicy(), order[:5], random.Random(0))


def test_play_after_applies_action_first():
    state = GameState(hand=mask_of(parse_cards("K1 M3 S5 K7 M8")))
    order = deck_orders(state.unseen, 1, seed=2)[0]
    final = play_after(state, Discard(parse_cards("K1")[0]), RULES, GreedyPolicy(), order, random.Random(0))
    assert parse_cards("K1")[0] in final.discarded_cards


def test_greedy_beats_random_on_common_decks():
    """Aynı 300 deste sırasında açgözlünün ortalaması rastgele politikadan yüksek olmalı."""
    orders = deck_orders(FULL_MASK, 300, seed=2026)
    greedy = [play_out(GameState(), RULES, GreedyPolicy(), o, policy_rng(2026, i)).score for i, o in enumerate(orders)]
    rand = [play_out(GameState(), RULES, RandomPolicy(), o, policy_rng(2026, i)).score for i, o in enumerate(orders)]
    assert sum(greedy) / len(greedy) > sum(rand) / len(rand)
