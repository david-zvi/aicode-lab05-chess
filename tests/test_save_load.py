import json
from pathlib import Path

import pytest

from game import new_position
from session import JSON, Session

MOVES = [("e2", "e4"), ("d7", "d5"), ("e4", "d5"), ("d8", "d5"), ("b1", "c3")]


def played(moves: list[tuple[str, str]] = MOVES, opponent: str = "human") -> Session:
    session = Session(opponent)
    for source, target in moves:
        session.play(source, target)
    return session


def round_trip(session: Session, tmp_path: Path) -> Session:
    """Save through a real file and load into a fresh session."""
    path = tmp_path / "game.json"
    path.write_text(json.dumps(session.save()))
    data: JSON = json.loads(path.read_text())
    loaded = Session()
    loaded.dispatch({"action": "load", "game": data})
    return loaded


def test_save_action_returns_the_saved_game() -> None:
    session = played()
    assert session.dispatch({"action": "save"}) == session.save()


def test_initial_game(tmp_path: Path) -> None:
    loaded = round_trip(Session(), tmp_path)
    assert loaded.position == new_position()
    assert loaded.view() == Session().view()


def test_game_after_several_moves(tmp_path: Path) -> None:
    original = played()
    loaded = round_trip(original, tmp_path)
    assert loaded.position == original.position
    assert loaded.view() == original.view()


def test_player_to_move(tmp_path: Path) -> None:
    assert round_trip(played(MOVES[:4]), tmp_path).view()["turn"] == "w"
    assert round_trip(played(MOVES), tmp_path).view()["turn"] == "b"


@pytest.mark.parametrize("opponent", ["human", "computer"])
def test_opponent_mode(opponent: str, tmp_path: Path) -> None:
    loaded = round_trip(played(MOVES[:2], opponent), tmp_path)
    assert loaded.opponent == opponent
    assert loaded.computer_to_move() is False


def test_computer_still_to_move_after_load(tmp_path: Path) -> None:
    loaded = round_trip(played(MOVES[:1], "computer"), tmp_path)
    assert loaded.computer_to_move()
    loaded.dispatch({"action": "computer-move"})
    assert len(loaded.notation) == 2


def test_move_notation(tmp_path: Path) -> None:
    original = played()
    assert round_trip(original, tmp_path).notation == original.notation
    assert original.notation[2] == "e4xd5"


def test_history_allows_undoing_earlier_moves(tmp_path: Path) -> None:
    loaded = round_trip(played(), tmp_path)
    for count in range(len(MOVES) - 1, -1, -1):
        loaded.dispatch({"action": "undo"})
        assert loaded.view() == played(MOVES[:count]).view()


def test_promotion_and_captures(tmp_path: Path) -> None:
    original = Session()
    original.dispatch({"action": "promotion-setup"})
    original.dispatch(
        {"action": "move", "source": "b7", "target": "a8", "promotion": "N"}
    )
    loaded = round_trip(original, tmp_path)
    assert loaded.view() == original.view()
    assert loaded.position.board["a8"] == "wN"
    assert loaded.captured == ["bP", "bR", "wP"]
    loaded.dispatch({"action": "undo"})
    assert loaded.position.board["b7"] == "wP"
    assert loaded.captured == ["bP", "wP"]


@pytest.mark.parametrize(
    "game",
    [
        None,  # no file chosen
        "not a game",
        [],
        {},
        {"opponent": "human"},
        {"opponent": "human", "moves": "e2e4"},
        {"opponent": "alien", "moves": []},
        {"opponent": "human", "moves": [["e2", "e4"]]},
        {"opponent": "human", "moves": [{"e2": "e4"}]},
        {"opponent": "human", "moves": [[None, "e4", None]]},
        {"opponent": "human", "moves": [["e2", 4, None]]},
        # promotion on a normal move
        {"opponent": "human", "moves": [["e2", "e4", "Q"]]},
        # illegal
        {"opponent": "human", "moves": [["e2", "e4", None], ["e4", "e5", None]]},
    ],
)
def test_invalid_save_is_rejected_and_game_kept(game: JSON) -> None:
    session = played(MOVES[:2])
    before = session.view()
    with pytest.raises(ValueError):
        session.dispatch({"action": "load", "game": game})
    assert session.view() == before
    assert len(session.history) == 2


def test_load_without_a_file_keeps_the_game() -> None:
    session = played(MOVES[:2])
    before = session.view()
    with pytest.raises(ValueError):
        session.dispatch({"action": "load"})
    assert session.view() == before
