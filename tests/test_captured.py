from session import Session


def test_display_after_capture_and_new_game():
    session = Session()
    assert session.view()["captured"] == []
    session.play("e2", "e4")
    session.play("d7", "d5")
    session.play("e4", "d5")
    assert session.view()["captured"] == ["bP"]
    session.dispatch({"action": "new"})
    assert session.view()["captured"] == []


def test_undo_restores_captured():
    session = Session()
    session.play("e2", "e4")
    session.play("d7", "d5")
    session.play("e4", "d5")
    session.dispatch({"action": "undo"})
    assert session.view()["captured"] == []


def test_promotion_is_not_a_capture():
    session = Session()
    session.dispatch({"action": "promotion-setup"})
    assert session.view()["captured"] == ["bP", "wP"]
    session.play("b7", "a8", "Q")
    assert session.view()["captured"] == ["bP", "bR", "wP"]
