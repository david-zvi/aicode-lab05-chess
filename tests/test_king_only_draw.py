import pytest

from computer import choose_move
from game import Position, legal_moves, move, new_position, status, winner
from session import Session


def kings_after_capture_session(opponent: str = "human") -> Session:
    """A session where White's next move, d4xe5, leaves only the two kings."""
    session = Session(opponent)
    session.position = Position({"d4": "wK", "e5": "bN", "h8": "bK"}, "w")
    return session


def test_king_versus_king_is_a_draw() -> None:
    position = Position({"e1": "wK", "e8": "bK"}, "w")
    assert status(position) == "kings-only"
    assert winner(position) is None


def test_capturing_the_last_piece_ends_the_game_in_a_draw() -> None:
    session = kings_after_capture_session()
    session.dispatch({"action": "move", "source": "d4", "target": "e5"})
    view = session.view()
    assert view["board"] == {"e5": "wK", "h8": "bK"}
    assert view["status"] == "kings-only"
    assert view["winner"] is None
    assert view["moves"] == ["d4xe5"]


@pytest.mark.parametrize(
    "extra",
    [
        {"a2": "wP"},
        {"a2": "bP"},
        {"c3": "wN"},
        {"c3": "bB"},
        {"a1": "wR"},
        {"a8": "bQ"},
    ],
)
def test_king_plus_another_piece_is_not_this_draw(extra: dict[str, str]) -> None:
    position = Position({"e1": "wK", "e8": "bK", **extra}, "w")
    assert status(position) != "kings-only"
    assert legal_moves(position, "e1")


def test_two_kings_of_one_colour_is_not_this_draw() -> None:
    # Not a real position, but the rule requires one king of each colour.
    position = Position({"e1": "wK", "e3": "wK", "e8": "bP"}, "w")
    assert status(position) != "kings-only"


def test_moves_are_rejected_after_the_draw() -> None:
    position = Position({"e1": "wK", "e8": "bK"}, "w")
    assert legal_moves(position, "e1") == []
    with pytest.raises(ValueError):
        move(position, "e1", "e2")
    assert position == Position({"e1": "wK", "e8": "bK"}, "w")


def test_session_rejects_moves_after_the_draw() -> None:
    session = kings_after_capture_session()
    session.dispatch({"action": "move", "source": "d4", "target": "e5"})
    assert session.legal("h8")["targets"] == []
    with pytest.raises(ValueError):
        session.dispatch({"action": "move", "source": "h8", "target": "g8"})
    assert session.position == Position({"e5": "wK", "h8": "bK"}, "b")
    assert session.notation == ["d4xe5"]


def test_computer_does_not_move_after_the_draw() -> None:
    session = kings_after_capture_session("computer")
    session.dispatch({"action": "move", "source": "d4", "target": "e5"})
    assert not session.computer_to_move()
    assert choose_move(session.position) is None
    with pytest.raises(ValueError):
        session.dispatch({"action": "computer-move"})


def test_new_game_clears_the_draw() -> None:
    session = kings_after_capture_session()
    session.dispatch({"action": "move", "source": "d4", "target": "e5"})
    session.dispatch({"action": "new"})
    view = session.view()
    assert view["status"] is None
    assert session.position == new_position()
    assert view["moves"] == []
    session.dispatch({"action": "move", "source": "e2", "target": "e4"})
    assert session.notation == ["e2-e4"]


def test_undo_leaves_the_draw() -> None:
    session = kings_after_capture_session()
    session.dispatch({"action": "move", "source": "d4", "target": "e5"})
    session.dispatch({"action": "undo"})
    view = session.view()
    assert view["status"] is None
    assert view["board"] == {"d4": "wK", "e5": "bN", "h8": "bK"}
