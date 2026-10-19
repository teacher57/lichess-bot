"""Openings the opponent can ask the bot to play, chosen with !opening in the game chat."""
import chess

# key -> (name, side the bot plays, line in UCI including both sides' moves)
OPENINGS = {
    "italian": ("Italian Game", chess.WHITE, "e2e4 e7e5 g1f3 b8c6 f1c4"),
    "ruy-lopez": ("Ruy Lopez", chess.WHITE, "e2e4 e7e5 g1f3 b8c6 f1b5"),
    "scotch": ("Scotch Game", chess.WHITE, "e2e4 e7e5 g1f3 b8c6 d2d4"),
    "kings-gambit": ("King's Gambit", chess.WHITE, "e2e4 e7e5 f2f4"),
    "queens-gambit": ("Queen's Gambit", chess.WHITE, "d2d4 d7d5 c2c4"),
    "english": ("English Opening", chess.WHITE, "c2c4"),
    "sicilian": ("Sicilian Defence", chess.BLACK, "e2e4 c7c5"),
    "french": ("French Defence", chess.BLACK, "e2e4 e7e6 d2d4 d7d5"),
    "caro-kann": ("Caro-Kann Defence", chess.BLACK, "e2e4 c7c6 d2d4 d7d5"),
    "scandinavian": ("Scandinavian Defence", chess.BLACK, "e2e4 d7d5"),
    "slav": ("Slav Defence", chess.BLACK, "d2d4 d7d5 c2c4 c7c6"),
    "kings-indian": ("King's Indian Defence", chess.BLACK, "d2d4 g8f6 c2c4 g7g6"),
    "dutch": ("Dutch Defence", chess.BLACK, "d2d4 f7f5"),
}

# game id -> chosen opening key
chosen_by_game: dict[str, str] = {}


def _on_line(key: str, moves: list[str]) -> bool:
    line = OPENINGS[key][2].split()
    return len(moves) < len(line) and line[:len(moves)] == moves


def possible(bot_color: chess.Color, moves: list[str]) -> list[str]:
    """Openings for the bot's side whose line the game still follows and hasn't finished."""
    return [key for key, (_, side, _) in OPENINGS.items() if side == bot_color and _on_line(key, moves)]


def name(key: str) -> str:
    """Full name of an opening."""
    return OPENINGS[key][0]


def next_move(board: chess.Board, game_id: str) -> tuple[chess.Move | None, str | None]:
    """
    The chosen line's next move for the bot, if any.

    :return: (move or None, chat message or None). The message is set when the opponent left the line.
    """
    key = chosen_by_game.get(game_id)
    if key is None:
        return None, None
    line = OPENINGS[key][2].split()
    moves = [m.uci() for m in board.move_stack]
    if line[:len(moves)] != moves[:len(line)]:
        del chosen_by_game[game_id]
        return None, f"You left the {name(key)} line, so I'll play my own moves now."
    if len(moves) >= len(line):
        del chosen_by_game[game_id]
        return None, None
    return chess.Move.from_uci(line[len(moves)]), None
