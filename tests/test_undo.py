from game import new_position
from session import Session, View


def play(session: Session, *moves: tuple[str, str]) -> None:
    for source, target in moves:
        session.dispatch({"action": "move", "source": source, "target": target})


def undo(session: Session) -> View:
    session.dispatch({"action": "undo"})
    return session.view()


def snapshot(session: Session) -> View:
    """A view whose board and moves can't change with later play."""
    return {
        **session.view(),
        "board": dict(session.position.board),
        "moves": list(session.notation),
    }


def computer_session() -> Session:
    session = Session()
    session.dispatch({"action": "new", "opponent": "computer"})
    return session


def test_undo_reverses_one_move_in_two_player_mode() -> None:
    session = Session()
    play(session, ("e2", "e4"), ("e7", "e5"))
    after_first = snapshot(session)
    play(session, ("g1", "f3"))
    view = undo(session)
    assert view["board"] == after_first["board"]
    assert view["turn"] == "w"
    assert view["moves"] == ["e2-e4", "e7-e5"]
    assert len(session.history) == 2


def test_repeated_undo_returns_to_the_start() -> None:
    session = Session()
    play(session, ("e2", "e4"), ("e7", "e5"), ("g1", "f3"))
    for remaining in (2, 1, 0):
        view = undo(session)
        assert len(view["moves"]) == remaining
    assert session.position == new_position()
    assert view["turn"] == "w"


def test_undo_at_the_start_does_nothing() -> None:
    session = Session()
    before = session.view()
    assert session.dispatch({"action": "undo"}) == before
    assert session.position == new_position()
    assert session.history == []


def test_undo_restores_a_captured_piece() -> None:
    session = Session()
    play(session, ("e2", "e4"), ("d7", "d5"), ("e4", "d5"))
    assert session.position.board["d5"] == "wP"
    assert len(session.position.board) == 31
    view = undo(session)
    assert view["board"]["d5"] == "bP"
    assert view["board"]["e4"] == "wP"
    assert len(view["board"]) == 32
    assert view["turn"] == "w"


def test_undo_restores_notation_and_play_continues() -> None:
    session = Session()
    play(session, ("e2", "e4"), ("d7", "d5"), ("e4", "d5"))
    assert session.view()["moves"] == ["e2-e4", "d7-d5", "e4xd5"]
    session.dispatch({"action": "undo"})
    play(session, ("e4", "e5"))
    assert session.view()["moves"] == ["e2-e4", "d7-d5", "e4-e5"]
    assert [entry["label"] for entry in session.history] == session.notation


def test_undo_restores_check_status() -> None:
    session = Session()
    play(session, ("e2", "e4"), ("f7", "f6"), ("d1", "h5"))
    assert session.view()["moves"][-1] == "d1-h5+"
    assert session.view()["status"] == "check"
    view = undo(session)
    assert view["status"] is None
    assert view["moves"] == ["e2-e4", "f7-f6"]


def test_undo_against_the_computer_reverses_reply_and_human_move() -> None:
    session = computer_session()
    play(session, ("e2", "e4"))
    session.dispatch({"action": "computer-move"})
    after_first_pair = snapshot(session)
    play(session, ("d2", "d4"))
    session.dispatch({"action": "computer-move"})
    assert len(session.notation) == 4
    view = undo(session)
    assert view["moves"] == after_first_pair["moves"]
    assert view["board"] == after_first_pair["board"]
    assert view["turn"] == "w"
    assert view["opponent"] == "computer"
    view = undo(session)
    assert view["moves"] == []
    assert session.position == new_position()


def test_undo_against_the_computer_before_its_reply() -> None:
    # Only the human's move is available to undo.
    session = computer_session()
    play(session, ("e2", "e4"))
    view = undo(session)
    assert view["moves"] == []
    assert view["turn"] == "w"
    assert session.position == new_position()


def test_undo_against_the_computer_at_the_start_does_nothing() -> None:
    session = computer_session()
    before = session.view()
    assert session.dispatch({"action": "undo"}) == before


def test_new_game_clears_undo_history() -> None:
    session = Session()
    play(session, ("e2", "e4"), ("e7", "e5"))
    session.dispatch({"action": "new", "opponent": "computer"})
    assert session.history == []
    view = undo(session)
    assert view["moves"] == []
    assert session.position == new_position()
    assert view["opponent"] == "computer"


def test_history_records_moves_for_replay() -> None:
    session = Session()
    play(session, ("e2", "e4"), ("e7", "e5"))
    assert [(e["source"], e["target"]) for e in session.history] == [
        ("e2", "e4"),
        ("e7", "e5"),
    ]
    assert session.history[0]["before"] == new_position()
    undone = session.undo()
    assert [(e["source"], e["target"]) for e in undone] == [("e7", "e5")]
