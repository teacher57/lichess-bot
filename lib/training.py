# SPDX-License-Identifier: MIT
# Copyright (c) 2026 teacher57. Written for teacher57-bot; see teacher57/LICENSE.
"""
Learning mode (!learn [chance]): after the opening (book and chosen line), on every move the bot looks for a
deliberate mistake that leaves the opponent a tactic: win at least a pawn, or mate, in 2-3 moves (never in 1).
When one is found, she plays it with the chosen chance (%) and says "Oops!".

Any opponent move that stays within TOLERANCE of the best line's result counts as on track. After the line's
length in moves, or checkmate, the bot says "Correct!". Leaving the line gets "Missed it." plus the best line.
Uses teacher57-bot's own search (chess-engine/engine.py), loaded from the engine directory in the config.
"""
import importlib.util
import os
import random
import time
from dataclasses import dataclass
import chess

DEFAULT_CHANCE = 30        # % chance to play a found mistake, when !learn has no number
MIN_GAIN = 100             # centipawns the opponent must win (a pawn)
UNIQUE_MARGIN = 100        # best first move must beat the 2nd best by this much
TOLERANCE = 50             # an opponent move counts if it keeps the result within this of the best line
FIND_SECONDS = 3.0         # time budget for finding a mistake, spent on every move after the opening
CHECK_SECONDS = 2.0        # time budget for checking one opponent move
LEARN_UNTIL_MOVE = 5       # !learn works until her 5th move

_engine_module = None


def _engine(engine_dir: str):
    """Load chess-engine/engine.py once (module name kept unique to avoid clashes)."""
    global _engine_module
    if _engine_module is None:
        path = os.path.join(os.path.abspath(engine_dir), "engine.py")
        spec = importlib.util.spec_from_file_location("teacher57_engine", path)
        assert spec and spec.loader
        _engine_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(_engine_module)
    return _engine_module


@dataclass
class Puzzle:
    mistake_ply: int           # index in move_stack of her mistake
    mistake: chess.Move
    moves: int                 # opponent moves in the line (2 or 3)
    target: int                # best line's score, opponent's view
    line_san: str              # best line from the position after her mistake


@dataclass
class Session:
    chance: int = DEFAULT_CHANCE
    puzzle: Puzzle | None = None


sessions: dict[str, Session] = {}


def her_moves_made(board: chess.Board, bot_is_white: bool) -> int:
    """How many moves the bot has played so far."""
    plies = len(board.move_stack)
    return (plies + 1) // 2 if bot_is_white else plies // 2


def _is_mate(score: int, mate: int) -> bool:
    return score > mate - 1000


def _search(eng, searcher, board: chess.Board, n: int, depth: int, seconds: float) -> tuple[list, int]:
    """Top-n moves at a fixed depth (side to move's view). Returns (ranked, depth reached)."""
    reached = [0]
    ranked = searcher.search_multipv(board, n, max_time=seconds, max_depth=depth,
                                     info=lambda d, *_: reached.__setitem__(0, d))
    return ranked, reached[0]


def _line(searcher, board: chess.Board, first: chess.Move, plies: int) -> list[chess.Move]:
    """Best line starting with `first`, following the searcher's transposition table."""
    line = board.copy()
    moves = [first]
    line.push(first)
    for _ in range(plies - 1):
        entry = searcher.tt.get(line._transposition_key())
        if not entry or entry[3] is None or entry[3] not in line.legal_moves:
            break
        moves.append(entry[3])
        line.push(entry[3])
    return moves


def _material(eng, board: chess.Board, color: chess.Color) -> int:
    """Material balance in centipawns from `color`'s view."""
    return sum(eng.VALUES[p.piece_type] * (1 if p.color == color else -1) for p in board.piece_map().values())


def _capture_balance(eng, board: chess.Board, alpha: int, beta: int, plies: int) -> int:
    """Material from the side to move's view after both sides make their best captures (alpha-beta)."""
    stand = _material(eng, board, board.turn)
    if plies == 0 or stand >= beta:
        return stand
    alpha = max(alpha, stand)
    for move in board.generate_legal_captures():
        board.push(move)
        score = -_capture_balance(eng, board, -beta, -alpha, plies - 1)
        board.pop()
        if score >= beta:
            return score
        alpha = max(alpha, score)
    return alpha


def _settled_material(eng, board: chess.Board, color: chess.Color) -> int:
    """Material from `color`'s view once pending captures are resolved (so a recapture still to come counts)."""
    balance = _capture_balance(eng, board.copy(), -10**9, 10**9, 6)
    return balance if board.turn == color else -balance


def _wins_in_one(eng, board: chess.Board, after: chess.Board) -> bool:
    """True if a single opponent move already mates or wins at least MIN_GAIN of material (after recaptures)."""
    them = after.turn
    before = _material(eng, board, them)
    for reply in after.legal_moves:
        after.push(reply)
        won = after.is_checkmate() or _settled_material(eng, after, them) - before >= MIN_GAIN
        after.pop()
        if won:
            return True
    return False


def find_mistake(board: chess.Board, engine_dir: str) -> tuple[chess.Move, Puzzle] | None:
    """Find a move for the bot that leaves the opponent a 2-3 move tactic, or None."""
    eng = _engine(engine_dir)
    searcher = eng.Searcher()
    deadline = time.monotonic() + FIND_SECONDS
    best, _ = _search(eng, searcher, board, 1, 3, FIND_SECONDS / 3)
    if not best:
        return None
    baseline = -best[0][1]  # opponent's view if she plays her best move
    candidates = [m for m in board.legal_moves if m != best[0][0]]
    random.shuffle(candidates)
    # Pass 1 (cheap): 2-move puzzles for every candidate. Pass 2: 3-move puzzles with the time left.
    not_in_one = []
    for moves in (2, 3):
        depth = 2 * moves - 1
        for mistake in candidates if moves == 2 else not_in_one:
            if time.monotonic() > deadline:
                return None
            after = board.copy()
            after.push(mistake)
            if after.is_game_over():
                continue
            if moves == 2:
                # Never winnable in 1 move: no single opponent move may already win a pawn of material (after
                # recaptures, so a free piece isn't hidden by her counter-captures), nor win by a 1-move search
                if _wins_in_one(eng, board, after):
                    continue
                one, _ = _search(eng, searcher, after, 1, 1, max(0.05, deadline - time.monotonic()))
                if not one or _is_mate(one[0][1], eng.MATE) or one[0][1] >= baseline + MIN_GAIN:
                    continue
                not_in_one.append(mistake)
            ranked, reached = _search(eng, searcher, after, 2, depth, deadline - time.monotonic())
            if reached < depth or not ranked:
                continue
            score = ranked[0][1]
            if not (_is_mate(score, eng.MATE) or score >= baseline + MIN_GAIN):
                continue
            if len(ranked) > 1 and score - ranked[1][1] < UNIQUE_MARGIN:
                continue  # more than one good answer: not a clean puzzle
            line = _line(searcher, after, ranked[0][0], depth)
            if not _is_mate(score, eng.MATE):
                # A real material win, not just positional bonuses: the line must end at least a pawn up
                end = after.copy()
                for move in line:
                    end.push(move)
                if _settled_material(eng, end, after.turn) - _material(eng, board, after.turn) < MIN_GAIN:
                    continue
            return mistake, Puzzle(len(board.move_stack), mistake, moves, score, after.variation_san(line))
    return None


def _on_track(board: chess.Board, puzzle: Puzzle, engine_dir: str) -> bool:
    """After an opponent move: is the opponent still winning as much as the best line (within TOLERANCE)?"""
    eng = _engine(engine_dir)
    done = (len(board.move_stack) - puzzle.mistake_ply) // 2  # opponent moves played since the mistake
    depth = max(0, 2 * (puzzle.moves - done))
    ranked, _ = _search(eng, eng.Searcher(), board, 1, max(1, depth), CHECK_SECONDS)
    if not ranked:
        return True
    score = -ranked[0][1]  # opponent's view
    if _is_mate(puzzle.target, eng.MATE):
        return _is_mate(score, eng.MATE)
    return score >= puzzle.target - TOLERANCE


def before_move(board: chess.Board, game_id: str, engine_dir: str) -> tuple[chess.Move | None, list[str]]:
    """
    Called on the bot's turn once the opening is over (no chosen-line or book move).
    Returns (move to play instead of the normal one, or None; chat messages).
    """
    session = sessions.get(game_id)
    if session is None:
        return None, []
    puzzle = session.puzzle
    if puzzle is not None:
        if len(board.move_stack) <= puzzle.mistake_ply or board.move_stack[puzzle.mistake_ply] != puzzle.mistake:
            session.puzzle = None  # taken back
            return None, []
        done = (len(board.move_stack) - puzzle.mistake_ply) // 2
        if not _on_track(board, puzzle, engine_dir):
            session.puzzle = None
            return None, [f"Missed it. The line was: {puzzle.line_san}"]
        if done >= puzzle.moves:
            session.puzzle = None
            return None, ["Correct!"]
        return None, []
    # Search first, then roll: every move after the opening takes about the same time
    found = find_mistake(board, engine_dir)
    if found is None or random.randint(1, 100) > session.chance:
        return None, []
    mistake, session.puzzle = found
    return mistake, ["Oops!"]


def on_game_over(board: chess.Board, game_id: str, bot_is_white: bool) -> list[str]:
    """Messages when the game ends: checkmating her during a puzzle counts as correct."""
    session = sessions.pop(game_id, None)
    if session and session.puzzle and board.is_checkmate() and board.turn == (chess.WHITE if bot_is_white else chess.BLACK):
        return ["Correct!"]
    return []
