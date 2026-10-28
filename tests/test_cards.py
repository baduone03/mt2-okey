import pytest

from okey.cards import (
    ALL_CARDS,
    FULL_MASK,
    Card,
    CardParseError,
    Color,
    card_from_index,
    cards_of,
    mask_of,
    parse_card,
    parse_cards,
)


def test_deck_has_24_unique_cards():
    assert len(ALL_CARDS) == 24
    assert len(set(ALL_CARDS)) == 24
    assert {c.color for c in ALL_CARDS} == set(Color)
    for color in Color:
        assert sorted(c.number for c in ALL_CARDS if c.color is color) == list(range(1, 9))


def test_index_and_bit_round_trip():
    assert [c.index for c in ALL_CARDS] == list(range(24))
    for card in ALL_CARDS:
        assert card_from_index(card.index) == card
        assert card.bit == 1 << card.index
    assert mask_of(ALL_CARDS) == FULL_MASK


@pytest.mark.parametrize("number", [0, 9, -1])
def test_invalid_number_rejected(number):
    with pytest.raises(ValueError, match="1-8"):
        Card(Color.RED, number)


def test_invalid_index_rejected():
    with pytest.raises(ValueError):
        card_from_index(24)


def test_mask_round_trip_and_duplicate_rejected():
    cards = (Card(Color.RED, 1), Card(Color.YELLOW, 8), Card(Color.BLUE, 4))
    assert set(cards_of(mask_of(cards))) == set(cards)
    with pytest.raises(ValueError, match="birden fazla"):
        mask_of([Card(Color.RED, 1), Card(Color.RED, 1)])


def test_cards_of_rejects_out_of_range_mask():
    with pytest.raises(ValueError):
        cards_of(1 << 24)


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("K5", Card(Color.RED, 5)),
        ("m3", Card(Color.BLUE, 3)),
        (" S 8 ", Card(Color.YELLOW, 8)),
        ("R1", Card(Color.RED, 1)),
        ("B2", Card(Color.BLUE, 2)),
        ("y7", Card(Color.YELLOW, 7)),
    ],
)
def test_parse_card(text, expected):
    assert parse_card(text) == expected


@pytest.mark.parametrize("text", ["", "K", "5", "X5", "K9", "K0", "KK5"])
def test_parse_card_errors(text):
    with pytest.raises(CardParseError):
        parse_card(text)


def test_parse_cards_and_duplicates():
    assert parse_cards("K5 M6, s7") == (
        Card(Color.RED, 5),
        Card(Color.BLUE, 6),
        Card(Color.YELLOW, 7),
    )
    assert parse_cards("  ") == ()
    with pytest.raises(CardParseError, match="iki kez"):
        parse_cards("K5 k5")


def test_card_code_round_trip():
    for card in ALL_CARDS:
        assert parse_card(card.code) == card
        assert str(card) == card.code
