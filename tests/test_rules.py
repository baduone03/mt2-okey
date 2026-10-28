from dataclasses import fields

import pytest

from okey.rules import (
    OFFICIAL_2026,
    PRESETS,
    UNVERIFIED_RULES,
    Chest,
    ChestThresholds,
    RuleConfig,
)


@pytest.mark.parametrize(
    ("score", "chest"),
    [
        (0, Chest.BRONZE),
        (290, Chest.BRONZE),
        (299, Chest.BRONZE),
        (300, Chest.SILVER),
        (399, Chest.SILVER),
        (400, Chest.GOLD),
        (560, Chest.GOLD),
    ],
)
def test_chest_boundaries(score, chest):
    assert OFFICIAL_2026.chest_for(score) is chest


def test_negative_score_rejected():
    with pytest.raises(ValueError):
        OFFICIAL_2026.chest_for(-10)


@pytest.mark.parametrize(("silver", "gold"), [(400, 400), (500, 400), (0, 400)])
def test_invalid_thresholds(silver, gold):
    with pytest.raises(ValueError):
        ChestThresholds(silver=silver, gold=gold)


def test_custom_thresholds():
    rules = RuleConfig(
        name="test",
        same_number_points=OFFICIAL_2026.same_number_points,
        same_color_run_points=OFFICIAL_2026.same_color_run_points,
        mixed_run_points=OFFICIAL_2026.mixed_run_points,
        chest_thresholds=ChestThresholds(silver=250, gold=350),
    )
    assert rules.chest_for(349) is Chest.SILVER
    assert rules.chest_for(350) is Chest.GOLD


@pytest.mark.parametrize(
    "overrides",
    [
        {"same_number_points": (20,) * 7},
        {"same_color_run_points": (50,) * 7},
        {"mixed_run_points": (10,) * 5},
        {"mixed_run_points": (10, 20, 30, 40, 50, -60)},
        {"hand_size": 2},
    ],
)
def test_invalid_config_rejected(overrides):
    base = {
        "name": "test",
        "same_number_points": OFFICIAL_2026.same_number_points,
        "same_color_run_points": OFFICIAL_2026.same_color_run_points,
        "mixed_run_points": OFFICIAL_2026.mixed_run_points,
    }
    with pytest.raises(ValueError):
        RuleConfig(**(base | overrides))


def test_official_defaults():
    assert OFFICIAL_2026.hand_size == 5
    assert OFFICIAL_2026.discard_requires_no_combo is False
    assert PRESETS["official_2026"] is OFFICIAL_2026


def test_unverified_rules_refer_to_real_fields():
    names = {f.name for f in fields(RuleConfig)}
    assert set(UNVERIFIED_RULES) <= names
