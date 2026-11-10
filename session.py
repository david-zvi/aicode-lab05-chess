"""Application actions and information shown beside the board."""

from computer import choose_move
from game import (
    copy_position,
    legal_moves,
    move,
    new_position,
    status,
    winner,
)


# Legal from the standard starting position under this game's rules.
# Next move: b7-a8, capturing a rook and reaching the last rank.
PROMOTION_SETUP = [
    ("a2", "a4"), ("h7", "h5"),
    ("a4", "a5"), ("h5", "h4"),
    ("a5", "a6"), ("h4", "h3"),
    ("a6", "b7"), ("h3", "g2"),
]


class Session:
    def __init__(self, opponent="human"):
        if opponent not in ("human", "computer"):
            raise ValueError("Unknown opponent")
        self.position = new_position()
        self.notation = []
        # One entry per played move, oldest first: the move, its label, and the
        # position before it. Undo restores from it; Save/Load and Redo can reuse it.
        self.history = []
        self.opponent = opponent

    def play(self, source, target):
        before = copy_position(self.position)
        label = move(self.position, source, target)
        self.history.append({"source": source, "target": target,
                             "label": label, "before": before})
        self.notation.append(label)
        self.after_move()

    def undo_one(self):
        """Reverse the latest move. Return its history entry, or None at the start."""
        if not self.history:
            return None
        entry = self.history.pop()
        self.position = copy_position(entry["before"])
        self.notation.pop()
        self.after_move()
        return entry

    def undo(self):
        """Undo one move, or against the computer, back to the human's turn.

        Return the undone history entries, latest first.
        """
        undone = []
        entry = self.undo_one()
        if entry:
            undone.append(entry)
        while (self.opponent == "computer" and self.history
               and self.position[1] == "b"):
            undone.append(self.undo_one())
        return undone

    def after_move(self):
        pass

    def view(self):
        return {
            "board": self.position[0],
            "turn": self.position[1],
            "moves": self.notation,
            "opponent": self.opponent,
            "status": status(self.position),
            "winner": winner(self.position),
            **self.sidebar(),
        }

    def computer_to_move(self):
        return (self.opponent == "computer" and self.position[1] == "b"
                and status(self.position) not in ("checkmate", "stalemate"))

    def sidebar(self):
        return {}

    def dispatch(self, action):
        command = action.get("action")
        if command == "move":
            if self.computer_to_move():
                raise ValueError("Wait for the computer's move")
            self.play(action.get("source"), action.get("target"))
        elif command == "computer-move":
            if not self.computer_to_move():
                raise ValueError("It is not the computer's turn")
            self.play(*choose_move(self.position))
        elif command == "legal":
            return {"targets": legal_moves(self.position, action.get("source"))}
        elif command == "undo":
            self.undo()
        elif command == "new":
            self.__init__(action.get("opponent", "human"))
        elif command == "promotion-setup":
            self.__init__()
            for source, target in PROMOTION_SETUP:
                self.play(source, target)
        else:
            raise ValueError("Unknown action")
        return self.view()
