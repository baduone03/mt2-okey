from collections import Counter
from itertools import combinations

import pytest

from okey.cards import ALL_CARDS, Card, Color, mask_of, parse_cards
from okey.combos import (
    ALL_COMBOS,
    ComboKind,
    InvalidComboError,
    classify,
    combos_in,
    make_combo,
    score,
)
from okey.rules import OFFICIAL_2026, RuleConfig

R, B, Y = Color.RED, Color.BLUE, Color.YELLOW

# docs/RULES.md bölüm 4'teki tablo; formülden değil, elle yazılmış değerler.
EXPECTED_SAME_NUMBER = {1: 20, 2: 30, 3: 40, 4: 50, 5: 60, 6: 70, 7: 80, 8: 90}
EXPECTED_SAME_COLOR_RUN = {1: 50, 2: 60, 3: 70, 4: 80, 5: 90, 6: 100}
EXPECTED_MIXED_RUN = {1: 10, 2: 20, 3: 30, 4: 40, 5: 50, 6: 60}


def test_combo_counts():
    counts = Counter(c.kind for c in ALL_COMBOS)
    assert counts[ComboKind.SAME_NUMBER] == 8
    assert counts[ComboKind.SAME_COLOR_RUN] == 18
    assert counts[ComboKind.MIXED_RUN] == 144
    assert len(ALL_COMBOS) == 170
    assert len({c.mask for c in ALL_COMBOS}) == 170


def test_all_combos_match_independent_enumeration():
    """Seri ve üçlüleri tanımdan ayrıca üretip ALL_COMBOS ile karşılaştırır."""
    expected = set()
    for n in range(1, 9):
        expected.add(mask_of(Card(color, n) for color in Color))
    for start in range(1, 7):
        for c1 in Color:
            for c2 in Color:
                for c3 in Color:
                    expected.add(
                        mask_of([Card(c1, start), Card(c2, start + 1), Card(c3, start + 2)])
                    )
    assert {c.mask for c in ALL_COMBOS} == expected


def test_every_combo_uses_three_distinct_cards():
    for combo in ALL_COMBOS:
        assert len(set(combo.cards)) == 3
        assert combo.mask.bit_count() == 3
        assert mask_of(combo.cards) == combo.mask


@pytest.mark.parametrize(("n", "points"), EXPECTED_SAME_NUMBER.items())
def test_same_number_points(n, points):
    cards = [Card(R, n), Card(B, n), Card(Y, n)]
    assert classify(cards) is ComboKind.SAME_NUMBER
    assert score(cards, OFFICIAL_2026) == points


@pytest.mark.parametrize(("start", "points"), EXPECTED_SAME_COLOR_RUN.items())
@pytest.mark.parametrize("color", list(Color))
def test_same_color_run_points(start, points, color):
    cards = [Card(color, start + i) for i in range(3)]
    assert classify(cards) is ComboKind.SAME_COLOR_RUN
    assert score(cards, OFFICIAL_2026) == points


@pytest.mark.parametrize(("start", "points"), EXPECTED_MIXED_RUN.items())
def test_mixed_run_points(start, points):
    for colors in [(R, B, Y), (R, R, B), (Y, B, Y), (B, Y, Y)]:
        cards = [Card(c, start + i) for i, c in enumerate(colors)]
        assert classify(cards) is ComboKind.MIXED_RUN
        assert score(cards, OFFICIAL_2026) == points


def test_every_combo_scored_from_table():
    tables = {
        ComboKind.SAME_NUMBER: EXPECTED_SAME_NUMBER,
        ComboKind.SAME_COLOR_RUN: EXPECTED_SAME_COLOR_RUN,
        ComboKind.MIXED_RUN: EXPECTED_MIXED_RUN,
    }
    for combo in ALL_COMBOS:
        assert combo.points(OFFICIAL_2026) == tables[combo.kind][combo.low]


def test_card_order_does_not_matter():
    assert score(parse_cards("S5 K3 M4"), OFFICIAL_2026) == 30
    assert str(make_combo(parse_cards("S5 K3 M4"))) == "K3-M4-S5"


@pytest.mark.parametrize(
    "text",
    [
        "K1 K2 K4",  # boşluklu seri
        "K7 K8 K1",  # döngü yok
        "K5 M5 M6",  # iki aynı numara + bir farklı
        "K1 M3 S5",
        "K2 K4 K6",
    ],
)
def test_invalid_triples(text):
    cards = parse_cards(text)
    assert classify(cards) is None
    with pytest.raises(InvalidComboError):
        make_combo(cards)


def test_same_card_twice_rejected():
    with pytest.raises(InvalidComboError, match="iki kez"):
        classify([Card(R, 3), Card(R, 3), Card(R, 4)])


@pytest.mark.parametrize("n_cards", [0, 2, 4])
def test_wrong_card_count_rejected(n_cards):
    with pytest.raises(InvalidComboError, match="tam 3"):
        classify(ALL_CARDS[:n_cards])


def test_classify_agrees_with_all_combos_over_every_triple():
    combo_masks = {c.mask for c in ALL_COMBOS}
    for triple in combinations(ALL_CARDS, 3):
        assert (classify(triple) is not None) == (mask_of(triple) in combo_masks)


def test_combos_in_hand():
    hand = mask_of(parse_cards("K3 K4 K5 M4 S4"))
    found = {str(c) for c in combos_in(hand)}
    assert found == {"K3-K4-K5", "K3-M4-K5", "K3-S4-K5", "K4-M4-S4"}
    assert combos_in(mask_of(parse_cards("K1 K8 M3 S5 M7"))) == []
    assert combos_in(0) == []


def test_custom_rules_change_score():
    rules = RuleConfig(
        name="özel",
        same_number_points=(1, 2, 3, 4, 5, 6, 7, 8),
        same_color_run_points=(11, 12, 13, 14, 15, 16),
        mixed_run_points=(21, 22, 23, 24, 25, 26),
    )
    assert score(parse_cards("K8 M8 S8"), rules) == 8
    assert score(parse_cards("M2 M3 M4"), rules) == 12
    assert score(parse_cards("M6 S7 M8"), rules) == 26
