"""Application actions and information shown beside the board."""

from computer import choose_move
from game import (
    copy_position,
    legal_moves,
    move,
    new_position,
    promotes,
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
        self.captured = []
        # One entry per played move, oldest first: the move, its label, and the
        # position before it. Undo restores from it; Save/Load and Redo can reuse it.
        self.history = []
        self.opponent = opponent

    def play(self, source, target, promotion=None):
        before = copy_position(self.position)
        # No en passant in this variant, so a capture is always on the target square.
        taken = self.position[0].get(target)
        label = move(self.position, source, target, promotion)
        self.history.append({"source": source, "target": target, "promotion": promotion,
                             "label": label, "before": before, "taken": taken})
        self.notation.append(label)
        if taken:
            self.captured = sorted(self.captured + [taken])

    def undo_one(self):
        """Reverse the latest move. Return its history entry, or None at the start."""
        if not self.history:
            return None
        entry = self.history.pop()
        self.position = copy_position(entry["before"])
        self.notation.pop()
        if entry["taken"]:
            self.captured.remove(entry["taken"])
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

    def load(self, game):
        """Replay a saved game into a fresh session; keep the current one if any step fails."""
        if not isinstance(game, dict) or not isinstance(game.get("moves"), list):
            raise ValueError("Not a saved game")
        loaded = type(self)(game.get("opponent"))
        for step in game["moves"]:
            if not isinstance(step, list) or len(step) != 3:
                raise ValueError("Not a saved game")
            loaded.play(*step)
        self.__dict__.update(vars(loaded))

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
        return {"captured": self.captured}

    def dispatch(self, action):
        command = action.get("action")
        if command == "move":
            if self.computer_to_move():
                raise ValueError("Wait for the computer's move")
            self.play(action.get("source"), action.get("target"), action.get("promotion"))
        elif command == "computer-move":
            if not self.computer_to_move():
                raise ValueError("It is not the computer's turn")
            self.play(*choose_move(self.position))
        elif command == "legal":
            source = action.get("source")
            targets = legal_moves(self.position, source)
            return {"targets": targets,
                    "promotions": [t for t in targets if promotes(self.position, source, t)]}
        elif command == "undo":
            self.undo()
        elif command == "new":
            self.__init__(action.get("opponent", "human"))
        elif command == "promotion-setup":
            self.__init__()
            for source, target in PROMOTION_SETUP:
                self.play(source, target)
        elif command == "save":
            # Board, turn, notation, captures and undo history are rebuilt by replaying on load.
            return {"opponent": self.opponent,
                    "moves": [[e["source"], e["target"], e["promotion"]] for e in self.history]}
        elif command == "load":
            self.load(action.get("game"))
        else:
            raise ValueError("Unknown action")
        return self.view()
