import pytest

from computer import evaluate
from game import Position, status
from session import Session


def test_unknown_action_is_rejected() -> None:
    with pytest.raises(ValueError, match="Unknown action"):
        Session().dispatch({"action": "fly"})


def test_stalemate_scores_zero_despite_material() -> None:
    position = Position({"a8": "bK", "b6": "wQ", "c6": "wK"}, "b")
    assert status(position) == "stalemate"
    assert evaluate(position, "w") == 0
    assert evaluate(position, "b") == 0
