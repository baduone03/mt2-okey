"""Oyun durumu, eylemler ve durum geçişleri.

`GameState` değişmezdir; `apply` yeni bir durum döndürür. Desteden gelecek kartlar
kullanıcı girene kadar bilinmediği için "görülmemiş" kartlar ile "destede kalan"
kartlar aynı kümedir.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from okey.cards import FULL_MASK, Card, cards_of
from okey.combos import Combo, combos_in
from okey.rules import RuleConfig


class Phase(Enum):
    AWAITING_DRAW = "kart bekleniyor"  # masa eksik ve destede kart var
    DECIDE = "karar"
    FINISHED = "bitti"  # deste boş ve masada geçerli üçlü yok


@dataclass(frozen=True)
class Draw:
    """Gözlem: desteden gelen kart masaya eklenir."""

    card: Card


@dataclass(frozen=True)
class Play:
    combo: Combo


@dataclass(frozen=True)
class Discard:
    card: Card


Action = Draw | Play | Discard


class IllegalActionError(ValueError):
    """Eylem mevcut durumda kurallara aykırı."""


@dataclass(frozen=True)
class GameState:
    hand: int = 0  # masadaki kartların maskesi
    played: tuple[Combo, ...] = ()  # oynanma sırasıyla
    discarded: int = 0
    score: int = 0

    def __post_init__(self) -> None:
        played_mask = 0
        for combo in self.played:
            if played_mask & combo.mask:
                raise ValueError(f"Bir kart birden fazla üçlüde kullanılmış: {combo}")
            played_mask |= combo.mask
        zones = (("masa", self.hand), ("oynanan", played_mask), ("atılan", self.discarded))
        for i, (name_a, mask_a) in enumerate(zones):
            if mask_a & ~FULL_MASK or mask_a < 0:
                raise ValueError(f"Geçersiz {name_a} maskesi: {mask_a:#x}")
            for name_b, mask_b in zones[i + 1 :]:
                if mask_a & mask_b:
                    shared = ", ".join(c.code for c in cards_of(mask_a & mask_b))
                    raise ValueError(f"Kart hem {name_a} hem {name_b} bölgesinde: {shared}")
        if self.score < 0:
            raise ValueError(f"Puan negatif olamaz: {self.score}")

    @property
    def played_mask(self) -> int:
        mask = 0
        for combo in self.played:
            mask |= combo.mask
        return mask

    @property
    def unseen(self) -> int:
        return FULL_MASK & ~(self.hand | self.played_mask | self.discarded)

    @property
    def deck_remaining(self) -> int:
        return self.unseen.bit_count()

    @property
    def hand_cards(self) -> tuple[Card, ...]:
        return cards_of(self.hand)

    @property
    def discarded_cards(self) -> tuple[Card, ...]:
        return cards_of(self.discarded)

    @property
    def unseen_cards(self) -> tuple[Card, ...]:
        return cards_of(self.unseen)

    def phase(self, rules: RuleConfig) -> Phase:
        if self.hand.bit_count() < rules.hand_size and self.unseen:
            return Phase.AWAITING_DRAW
        if not self.unseen and not combos_in(self.hand):
            return Phase.FINISHED
        return Phase.DECIDE


def can_discard(state: GameState, rules: RuleConfig) -> bool:
    return not (rules.discard_requires_no_combo and combos_in(state.hand))


def legal_actions(state: GameState, rules: RuleConfig) -> list[Action]:
    phase = state.phase(rules)
    if phase is Phase.AWAITING_DRAW:
        return [Draw(card) for card in state.unseen_cards]
    if phase is Phase.FINISHED:
        return []
    actions: list[Action] = [Play(combo) for combo in combos_in(state.hand)]
    if can_discard(state, rules):
        actions.extend(Discard(card) for card in state.hand_cards)
    return actions


def apply(state: GameState, action: Action, rules: RuleConfig) -> GameState:
    """Eylemi uygular ve yeni durumu döndürür; kurala aykırıysa IllegalActionError verir."""
    phase = state.phase(rules)
    if phase is Phase.FINISHED:
        raise IllegalActionError("Oyun bitti; yeni eylem yapılamaz.")

    if isinstance(action, Draw):
        card = action.card
        if phase is not Phase.AWAITING_DRAW:
            raise IllegalActionError(
                f"{card} çekilemez: masa dolu ({rules.hand_size} kart), önce oynayın veya atın."
            )
        if not state.unseen & card.bit:
            raise IllegalActionError(f"{card} zaten görüldü (masada, oynanmış veya atılmış).")
        return GameState(state.hand | card.bit, state.played, state.discarded, state.score)

    if phase is not Phase.DECIDE:
        raise IllegalActionError(
            f"Masa eksik: önce desteden gelen kartları girin ({state.hand.bit_count()}/{rules.hand_size})."
        )

    if isinstance(action, Play):
        combo = action.combo
        if combo.mask & state.hand != combo.mask:
            raise IllegalActionError(f"{combo} oynanamaz: kartların hepsi masada değil.")
        return GameState(
            state.hand & ~combo.mask,
            state.played + (combo,),
            state.discarded,
            state.score + combo.points(rules),
        )

    if isinstance(action, Discard):
        card = action.card
        if not state.hand & card.bit:
            raise IllegalActionError(f"{card} atılamaz: masada değil.")
        if not can_discard(state, rules):
            raise IllegalActionError(
                f"{card} atılamaz: masada geçerli üçlü varken kart atmak bu kurallarda yasak."
            )
        return GameState(state.hand & ~card.bit, state.played, state.discarded | card.bit, state.score)

    raise TypeError(f"Bilinmeyen eylem türü: {action!r}")
