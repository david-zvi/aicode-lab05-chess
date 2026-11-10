"""Application actions and information shown beside the board."""

from typing import TypedDict

from computer import choose_move
from game import (
    Board,
    Position,
    copy_position,
    legal_moves,
    move,
    new_position,
    promotes,
    status,
    winner,
)

# Any value json.loads can return.
type JSON = dict[str, JSON] | list[JSON] | str | int | float | bool | None

# Legal from the standard starting position under this game's rules.
# Next move: b7-a8, capturing a rook and reaching the last rank.
PROMOTION_SETUP = [
    ("a2", "a4"),
    ("h7", "h5"),
    ("a4", "a5"),
    ("h5", "h4"),
    ("a5", "a6"),
    ("h4", "h3"),
    ("a6", "b7"),
    ("h3", "g2"),
]


class HistoryEntry(TypedDict):
    source: str
    target: str
    promotion: str | None
    label: str
    before: Position
    taken: str | None


class View(TypedDict):
    board: Board
    turn: str
    moves: list[str]
    opponent: str
    status: str | None
    winner: str | None
    captured: list[str]


class Legal(TypedDict):
    targets: list[str]
    promotions: list[str]


class SavedGame(TypedDict):
    opponent: str
    moves: list[list[str | None]]


def text(value: JSON) -> str:
    """Narrow a browser-supplied value to a string."""
    if isinstance(value, str):
        return value
    raise ValueError("Expected text")


def optional_text(value: JSON) -> str | None:
    if value is None:
        return None
    return text(value)


def saved_game(game: JSON) -> tuple[str, list[tuple[str, str, str | None]]]:
    """Narrow a loaded file to its opponent and (source, target, promotion) steps."""
    if isinstance(game, dict):
        moves = game.get("moves")
        if isinstance(moves, list):
            return text(game.get("opponent")), [saved_step(step) for step in moves]
    raise ValueError("Not a saved game")


def saved_step(step: JSON) -> tuple[str, str, str | None]:
    if isinstance(step, list) and len(step) == 3:
        source, target, promotion = step
        return text(source), text(target), optional_text(promotion)
    raise ValueError("Not a saved game")


class Session:
    def __init__(self, opponent: str = "human") -> None:
        if opponent not in ("human", "computer"):
            raise ValueError("Unknown opponent")
        self.position: Position = new_position()
        self.notation: list[str] = []
        self.captured: list[str] = []
        # One entry per played move, oldest first: the move, its label, and the
        # position before it. Undo restores from it; Save/Load and Redo can reuse it.
        self.history: list[HistoryEntry] = []
        self.opponent = opponent

    def play(self, source: str, target: str, promotion: str | None = None) -> None:
        before = copy_position(self.position)
        # No en passant in this variant, so a capture is always on the target square.
        taken = self.position.board.get(target)
        label = move(self.position, source, target, promotion)
        self.history.append(
            {
                "source": source,
                "target": target,
                "promotion": promotion,
                "label": label,
                "before": before,
                "taken": taken,
            }
        )
        self.notation.append(label)
        if taken:
            self.captured = sorted(self.captured + [taken])

    def undo_one(self) -> HistoryEntry | None:
        """Reverse the latest move. Return its history entry, or None at the start."""
        if not self.history:
            return None
        entry = self.history.pop()
        self.position = copy_position(entry["before"])
        self.notation.pop()
        if entry["taken"]:
            self.captured.remove(entry["taken"])
        return entry

    def undo(self) -> list[HistoryEntry]:
        """Undo one move, or against the computer, back to the human's turn.

        Return the undone history entries, latest first.
        """
        undone: list[HistoryEntry] = []
        entry = self.undo_one()
        while entry:
            undone.append(entry)
            if not (self.opponent == "computer" and self.position.turn == "b"):
                break
            entry = self.undo_one()
        return undone

    def legal(self, source: str) -> Legal:
        targets = legal_moves(self.position, source)
        return {
            "targets": targets,
            "promotions": [t for t in targets if promotes(self.position, source, t)],
        }

    def save(self) -> SavedGame:
        # Board, turn, notation, captures and undo history are rebuilt by replaying on load.
        return {
            "opponent": self.opponent,
            "moves": [[e["source"], e["target"], e["promotion"]] for e in self.history],
        }

    def load(self, game: JSON) -> None:
        """Replay a saved game into a fresh session; keep the current one if any step fails."""
        opponent, steps = saved_game(game)
        loaded = type(self)(opponent)
        for step in steps:
            loaded.play(*step)
        self.__dict__.update(vars(loaded))

    def view(self) -> View:
        return {
            "board": self.position.board,
            "turn": self.position.turn,
            "moves": self.notation,
            "opponent": self.opponent,
            "status": status(self.position),
            "winner": winner(self.position),
            "captured": self.captured,
        }

    def computer_to_move(self) -> bool:
        return (
            self.opponent == "computer"
            and self.position.turn == "b"
            and status(self.position) not in ("checkmate", "stalemate", "kings-only")
        )

    def dispatch(self, action: dict[str, JSON]) -> View | Legal | SavedGame:
        command = action.get("action")
        if command == "move":
            if self.computer_to_move():
                raise ValueError("Wait for the computer's move")
            self.play(
                text(action.get("source")),
                text(action.get("target")),
                optional_text(action.get("promotion")),
            )
        elif command == "computer-move":
            if not self.computer_to_move():
                raise ValueError("It is not the computer's turn")
            chosen = choose_move(self.position)
            # computer_to_move() excludes finished games, so a move always exists.
            assert chosen is not None
            self.play(*chosen)
        elif command == "legal":
            return self.legal(text(action.get("source")))
        elif command == "undo":
            self.undo()
        elif command == "new":
            self.__dict__.update(
                vars(type(self)(text(action.get("opponent", "human"))))
            )
        elif command == "promotion-setup":
            self.__dict__.update(vars(type(self)()))
            for source, target in PROMOTION_SETUP:
                self.play(source, target)
        elif command == "save":
            return self.save()
        elif command == "load":
            self.load(action.get("game"))
        else:
            raise ValueError("Unknown action")
        return self.view()
