"""Openings the opponent can ask the bot to play: a named one with !opening, or any line typed with !line."""
import re
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

# game id -> (name of the line, line in UCI including both sides' moves)
chosen_by_game: dict[str, tuple[str, list[str]]] = {}


def _on_line(line: list[str], moves: list[str]) -> bool:
    return len(moves) < len(line) and line[:len(moves)] == moves


def possible(bot_color: chess.Color, moves: list[str]) -> list[str]:
    """Openings for the bot's side whose line the game still follows and hasn't finished."""
    return [key for key, (_, side, line) in OPENINGS.items() if side == bot_color and _on_line(line.split(), moves)]


def name(key: str) -> str:
    """Full name of an opening."""
    return OPENINGS[key][0]


def choose(game_id: str, key: str) -> None:
    """Make the bot play the named opening in this game."""
    chosen_by_game[game_id] = (f"the {name(key)}", OPENINGS[key][2].split())


def parse_line(text: str) -> list[str]:
    """
    Read a line typed in chat, from the start of the game: SAN or UCI, move numbers optional ("1. e4 e5 2. Nf3").

    :return: the line in UCI.
    :raises ValueError: with a message for the chat when a move can't be read or isn't legal.
    """
    board = chess.Board()
    for token in text.split():
        token = re.sub(r"^\d+\.+", "", token).rstrip("!?")  # "1.e4", "3...Nc6", "Bc4!?"
        if not token:
            continue
        move = None
        for candidate in (token, token[0].upper() + token[1:]):  # "nf3" -> "Nf3"
            try:
                move = board.parse_san(candidate)
                break
            except ValueError:
                pass
        if move is None:
            try:
                move = chess.Move.from_uci(token.lower())
            except ValueError:
                move = None
            if move is None or not board.is_legal(move):
                raise ValueError(f"I can't play '{token}' after {describe([m.uci() for m in board.move_stack]) or 'the start'}.")
        board.push(move)
    if not board.move_stack:
        raise ValueError("The line has no moves.")
    return [m.uci() for m in board.move_stack]


def set_line(game_id: str, bot_color: chess.Color, moves: list[str], line: list[str]) -> str | None:
    """
    Make the bot follow a custom line in this game.

    :return: why the line can't be used, or None when it was set.
    """
    if line[:len(moves)] != moves[:len(line)]:
        return "That line doesn't match the moves played so far."
    bot_moves_left = [ply for ply in range(len(moves), len(line)) if (ply % 2 == 0) == (bot_color == chess.WHITE)]
    if not bot_moves_left:
        return "That line has no moves left for me."
    chosen_by_game[game_id] = ("your line", line)
    return None


def describe(line: list[str]) -> str:
    """The line in SAN with move numbers."""
    return chess.Board().variation_san([chess.Move.from_uci(m) for m in line])


def next_move(board: chess.Board, game_id: str) -> tuple[chess.Move | None, str | None]:
    """
    The chosen line's next move for the bot, if any.

    :return: (move or None, chat message or None). The message is set when the opponent left the line.
    """
    chosen = chosen_by_game.get(game_id)
    if chosen is None:
        return None, None
    line_name, line = chosen
    moves = [m.uci() for m in board.move_stack]
    if line[:len(moves)] != moves[:len(line)]:
        del chosen_by_game[game_id]
        return None, f"You left {line_name}, so I'll play my own moves now."
    if len(moves) >= len(line):
        del chosen_by_game[game_id]
        return None, None
    return chess.Move.from_uci(line[len(moves)]), None
