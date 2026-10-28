"""Oyun oturumu: olay günlüğü (event sourcing) ve geri alma.

Durum hiçbir zaman doğrudan değiştirilmez; her eylem günlüğe eklenir ve durum,
olayların sırayla uygulanmasıyla elde edilir. Geri almak son olayı çıkarmaktır, bu
yüzden kart sayımı ve puan geçmişle her zaman tutarlıdır. Ara durumlar önbellekte
tutulur; `replay()` ile günlükten sıfırdan yeniden hesaplanabilir.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass, field

from okey.cards import Card
from okey.combos import make_combo
from okey.rules import OFFICIAL_2026, RuleConfig
from okey.state import (
    Action,
    Discard,
    Draw,
    GameState,
    IllegalActionError,
    Phase,
    Play,
    apply,
)


class NothingToUndoError(ValueError):
    """Geri alınacak eylem yok."""


@dataclass(frozen=True)
class HistoryEntry:
    index: int  # 1'den başlar
    action: Action
    state_after: GameState


@dataclass(frozen=True)
class GameSession:
    rules: RuleConfig = OFFICIAL_2026
    events: tuple[Action, ...] = ()
    # states[i]: i olay uygulandıktan sonraki durum. Verilmezse günlükten hesaplanır.
    states: tuple[GameState, ...] | None = field(default=None, repr=False, compare=False)

    def __post_init__(self) -> None:
        if self.states is None:
            object.__setattr__(self, "states", _fold(self.events, self.rules))
        elif len(self.states) != len(self.events) + 1:
            raise ValueError("Durum önbelleği olay sayısıyla uyuşmuyor.")

    @property
    def state(self) -> GameState:
        return self.states[-1]

    @property
    def phase(self) -> Phase:
        return self.state.phase(self.rules)

    @property
    def can_undo(self) -> bool:
        return bool(self.events)

    def act(self, action: Action) -> GameSession:
        """Eylemi uygular; kurala aykırıysa IllegalActionError verir ve oturum değişmez."""
        new_state = apply(self.state, action, self.rules)
        return GameSession(self.rules, self.events + (action,), self.states + (new_state,))

    def draw(self, card: Card) -> GameSession:
        return self.act(Draw(card))

    def play(self, cards: Iterable[Card]) -> GameSession:
        return self.act(Play(make_combo(cards)))

    def discard(self, card: Card) -> GameSession:
        return self.act(Discard(card))

    def undo(self) -> GameSession:
        if not self.events:
            raise NothingToUndoError("Geri alınacak eylem yok.")
        return GameSession(self.rules, self.events[:-1], self.states[:-1])

    def remove_draw(self, card: Card) -> GameSession:
        """Yanlış girilmiş bir kartı masadan kaldırır.

        Yalnızca kartın girilmesinden sonra sadece başka kart girişleri yapılmışsa
        mümkündür; araya oynama/atma girdiyse önce onlar geri alınmalıdır.
        """
        try:
            i = self.events.index(Draw(card))
        except ValueError:
            raise IllegalActionError(f"{card} için bir kart girişi yok.") from None
        if any(not isinstance(e, Draw) for e in self.events[i + 1 :]):
            raise IllegalActionError(
                f"{card} girildikten sonra oynama/atma yapılmış; önce onları geri alın."
            )
        return GameSession(self.rules, self.events[:i] + self.events[i + 1 :])

    def new_game(self) -> GameSession:
        return GameSession(self.rules)

    def with_rules(self, rules: RuleConfig) -> GameSession:
        """Aynı günlüğü yeni kurallarla yeniden oynatır; uyumsuzsa IllegalActionError verir."""
        return GameSession(rules, self.events)

    def replay(self) -> GameState:
        """Önbelleği kullanmadan günlükten son durumu yeniden hesaplar."""
        return _fold(self.events, self.rules)[-1]

    @property
    def history(self) -> list[HistoryEntry]:
        return [
            HistoryEntry(i, action, state)
            for i, (action, state) in enumerate(zip(self.events, self.states[1:]), start=1)
        ]


def _fold(events: Iterable[Action], rules: RuleConfig) -> tuple[GameState, ...]:
    states = [GameState()]
    for action in events:
        states.append(apply(states[-1], action, rules))
    return tuple(states)


def describe_action(action: Action, rules: RuleConfig) -> str:
    if isinstance(action, Draw):
        return f"Çekildi: {action.card}"
    if isinstance(action, Play):
        combo = action.combo
        return f"Oynandı: {combo} ({combo.kind.value}, +{combo.points(rules)})"
    if isinstance(action, Discard):
        return f"Atıldı: {action.card}"
    raise TypeError(f"Bilinmeyen eylem türü: {action!r}")
