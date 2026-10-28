"""Kart tablosu etkileşim mantığı (arayüzden bağımsız).

Streamlit arayüzü yalnızca bu fonksiyonları çağırır; böylece "karta tıklayınca ne olur"
sorusu pytest ile doğrudan test edilebilir.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from okey.cards import Card
from okey.combos import InvalidComboError, classify, make_combo
from okey.session import GameSession
from okey.state import Action, Discard, GameState, IllegalActionError, Phase, Play, can_discard


class Zone(Enum):
    UNSEEN = "görülmemiş"
    HAND = "masada"
    PLAYED = "oynandı"
    DISCARDED = "atıldı"


def card_zone(state: GameState, card: Card) -> Zone:
    if state.hand & card.bit:
        return Zone.HAND
    if state.discarded & card.bit:
        return Zone.DISCARDED
    if state.played_mask & card.bit:
        return Zone.PLAYED
    return Zone.UNSEEN


@dataclass(frozen=True)
class ClickResult:
    session: GameSession
    selection: frozenset[Card]
    message: str | None = None  # kullanıcıya gösterilecek uyarı


def handle_card_click(
    session: GameSession, selection: frozenset[Card], card: Card
) -> ClickResult:
    """Kart tablosunda bir karta tıklanınca oturumu ve seçimi günceller.

    - Kart bekleniyorken görülmemiş karta tıklamak onu masaya ekler; masadaki bir
      karta tekrar tıklamak yanlış girişi geri alır.
    - Karar aşamasında masadaki kartlara tıklamak seçimi değiştirir.
    """
    state = session.state
    phase = session.phase
    zone = card_zone(state, card)

    if phase is Phase.FINISHED:
        return ClickResult(session, frozenset(), "Oyun bitti. Yeni oyun başlatın veya geri alın.")
    if zone in (Zone.PLAYED, Zone.DISCARDED):
        return ClickResult(
            session, selection, f"{card} zaten {zone.value}; düzeltmek için Geri al'ı kullanın."
        )

    if phase is Phase.AWAITING_DRAW:
        try:
            if zone is Zone.UNSEEN:
                return ClickResult(session.draw(card), frozenset())
            return ClickResult(session.remove_draw(card), frozenset())
        except IllegalActionError as exc:
            return ClickResult(session, selection, str(exc))

    # Phase.DECIDE
    if zone is Zone.UNSEEN:
        return ClickResult(
            session, selection, "Masa dolu: önce bir üçlü oynayın veya bir kart atın."
        )
    return ClickResult(session, selection ^ {card})


def selected_action(
    session: GameSession, selection: frozenset[Card]
) -> tuple[Action | None, str]:
    """Seçili kartlardan yapılabilecek eylemi ve bir açıklamayı döndürür."""
    if session.phase is not Phase.DECIDE:
        return None, ""
    if len(selection) == 1:
        (card,) = selection
        if not can_discard(session.state, session.rules):
            return None, "Masada geçerli üçlü varken kart atmak bu kurallarda yasak."
        return Discard(card), f"{card} atılabilir."
    if len(selection) == 3:
        try:
            if classify(selection) is None:
                return None, "Seçili kartlar geçerli bir üçlü değil."
            combo = make_combo(selection)
        except InvalidComboError as exc:
            return None, str(exc)
        return Play(combo), f"{combo} ({combo.kind.value}) +{combo.points(session.rules)} puan."
    if not selection:
        return None, "Oynamak için 3 kart, atmak için 1 kart seçin."
    return None, f"{len(selection)} kart seçili: oynamak için 3, atmak için 1 kart seçin."
