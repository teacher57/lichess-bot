"""Classical chess engine: alpha-beta search + piece-square-table evaluation.

Move generation comes from python-chess; this file is only search and eval.
"""
import time

import chess

# Piece values (centipawns)
VALUES = {chess.PAWN: 100, chess.KNIGHT: 320, chess.BISHOP: 330,
          chess.ROOK: 500, chess.QUEEN: 900, chess.KING: 0}

# Piece-square tables from White's view, a8..h8 first row (index with square ^ 56 for White).
PST = {
    chess.PAWN: [
        0, 0, 0, 0, 0, 0, 0, 0,
        50, 50, 50, 50, 50, 50, 50, 50,
        10, 10, 20, 30, 30, 20, 10, 10,
        5, 5, 10, 25, 25, 10, 5, 5,
        0, 0, 0, 20, 20, 0, 0, 0,
        5, -5, -10, 0, 0, -10, -5, 5,
        5, 10, 10, -20, -20, 10, 10, 5,
        0, 0, 0, 0, 0, 0, 0, 0],
    chess.KNIGHT: [
        -50, -40, -30, -30, -30, -30, -40, -50,
        -40, -20, 0, 0, 0, 0, -20, -40,
        -30, 0, 10, 15, 15, 10, 0, -30,
        -30, 5, 15, 20, 20, 15, 5, -30,
        -30, 0, 15, 20, 20, 15, 0, -30,
        -30, 5, 10, 15, 15, 10, 5, -30,
        -40, -20, 0, 5, 5, 0, -20, -40,
        -50, -40, -30, -30, -30, -30, -40, -50],
    chess.BISHOP: [
        -20, -10, -10, -10, -10, -10, -10, -20,
        -10, 0, 0, 0, 0, 0, 0, -10,
        -10, 0, 5, 10, 10, 5, 0, -10,
        -10, 5, 5, 10, 10, 5, 5, -10,
        -10, 0, 10, 10, 10, 10, 0, -10,
        -10, 10, 10, 10, 10, 10, 10, -10,
        -10, 5, 0, 0, 0, 0, 5, -10,
        -20, -10, -10, -10, -10, -10, -10, -20],
    chess.ROOK: [
        0, 0, 0, 0, 0, 0, 0, 0,
        5, 10, 10, 10, 10, 10, 10, 5,
        -5, 0, 0, 0, 0, 0, 0, -5,
        -5, 0, 0, 0, 0, 0, 0, -5,
        -5, 0, 0, 0, 0, 0, 0, -5,
        -5, 0, 0, 0, 0, 0, 0, -5,
        -5, 0, 0, 0, 0, 0, 0, -5,
        0, 0, 0, 5, 5, 0, 0, 0],
    chess.QUEEN: [
        -20, -10, -10, -5, -5, -10, -10, -20,
        -10, 0, 0, 0, 0, 0, 0, -10,
        -10, 0, 5, 5, 5, 5, 0, -10,
        -5, 0, 5, 5, 5, 5, 0, -5,
        0, 0, 5, 5, 5, 5, 0, -5,
        -10, 5, 5, 5, 5, 5, 0, -10,
        -10, 0, 5, 0, 0, 0, 0, -10,
        -20, -10, -10, -5, -5, -10, -10, -20],
}
KING_MID = [
    -30, -40, -40, -50, -50, -40, -40, -30,
    -30, -40, -40, -50, -50, -40, -40, -30,
    -30, -40, -40, -50, -50, -40, -40, -30,
    -30, -40, -40, -50, -50, -40, -40, -30,
    -20, -30, -30, -40, -40, -30, -30, -20,
    -10, -20, -20, -20, -20, -20, -20, -10,
    20, 20, 0, 0, 0, 0, 20, 20,
    20, 30, 10, 0, 0, 10, 30, 20]
KING_END = [
    -50, -40, -30, -20, -20, -30, -40, -50,
    -30, -20, -10, 0, 0, -10, -20, -30,
    -30, -10, 20, 30, 30, 20, -10, -30,
    -30, -10, 30, 40, 40, 30, -10, -30,
    -30, -10, 30, 40, 40, 30, -10, -30,
    -30, -10, 20, 30, 30, 20, -10, -30,
    -30, -30, 0, 0, 0, 0, -30, -30,
    -50, -30, -30, -30, -30, -30, -30, -50]

MATE = 100_000
INF = 10 ** 9


def evaluate(board: chess.Board) -> int:
    """Static eval in centipawns from the side to move's view."""
    score = 0
    non_pawn = 0
    for piece_type in (chess.KNIGHT, chess.BISHOP, chess.ROOK, chess.QUEEN):
        non_pawn += VALUES[piece_type] * len(board.pieces(piece_type, chess.WHITE) | board.pieces(piece_type, chess.BLACK))
    # 0 = opening (all pieces), 1 = bare endgame
    phase = max(0.0, min(1.0, 1 - non_pawn / 6200))

    for color, sign in ((chess.WHITE, 1), (chess.BLACK, -1)):
        for piece_type, table in PST.items():
            for sq in board.pieces(piece_type, color):
                idx = sq ^ 56 if color == chess.WHITE else sq
                score += sign * (VALUES[piece_type] + table[idx])
        king_sq = board.king(color)
        if king_sq is not None:
            idx = king_sq ^ 56 if color == chess.WHITE else king_sq
            score += sign * round(KING_MID[idx] * (1 - phase) + KING_END[idx] * phase)
        if len(board.pieces(chess.BISHOP, color)) >= 2:
            score += sign * 30

    return score if board.turn == chess.WHITE else -score


class TimeUp(Exception):
    pass


class Searcher:
    def __init__(self):
        self.tt = {}  # key -> (depth, score, flag, move)
        self.killers = {}
        self.history = {}
        self.nodes = 0
        self.deadline = None

    def order(self, board, moves, tt_move, ply):
        killers = self.killers.get(ply, ())

        def key(m):
            if m == tt_move:
                return 10_000_000
            if board.is_capture(m):
                victim = board.piece_type_at(m.to_square) or chess.PAWN  # en passant
                attacker = board.piece_type_at(m.from_square)
                return 1_000_000 + VALUES[victim] * 10 - VALUES[attacker] // 10
            if m.promotion:
                return 900_000
            if m in killers:
                return 800_000
            return self.history.get((m.from_square, m.to_square), 0)
        return sorted(moves, key=key, reverse=True)

    def check_time(self):
        self.nodes += 1
        if self.deadline and self.nodes & 1023 == 0 and time.monotonic() > self.deadline:
            raise TimeUp

    def quiesce(self, board, alpha, beta, ply):
        self.check_time()
        stand = evaluate(board)
        if stand >= beta:
            return beta
        alpha = max(alpha, stand)
        captures = [m for m in board.generate_legal_captures()]
        for m in self.order(board, captures, None, ply):
            board.push(m)
            score = -self.quiesce(board, -beta, -alpha, ply + 1)
            board.pop()
            if score >= beta:
                return beta
            alpha = max(alpha, score)
        return alpha

    def negamax(self, board, depth, alpha, beta, ply):
        self.check_time()
        if ply > 0 and (board.is_repetition(2) or board.halfmove_clock >= 100 or board.is_insufficient_material()):
            return 0

        in_check = board.is_check()
        if in_check:
            depth += 1  # check extension
        if depth <= 0:
            return self.quiesce(board, alpha, beta, ply)

        key = board._transposition_key()
        entry = self.tt.get(key)
        tt_move = None
        if entry:
            e_depth, e_score, e_flag, tt_move = entry
            if ply > 0 and e_depth >= depth:
                if e_flag == 0 or (e_flag == 1 and e_score >= beta) or (e_flag == -1 and e_score <= alpha):
                    return e_score

        # Null-move pruning: skip a turn; if still >= beta, this node is too good.
        if ply > 0 and not in_check and depth >= 3 and self._has_pieces(board):
            board.push(chess.Move.null())
            score = -self.negamax(board, depth - 3, -beta, -beta + 1, ply + 1)
            board.pop()
            if score >= beta:
                return beta

        moves = list(board.legal_moves)
        if not moves:
            return -MATE + ply if in_check else 0

        orig_alpha = alpha
        best_move, best = None, -INF
        for i, m in enumerate(self.order(board, moves, tt_move, ply)):
            quiet = not board.is_capture(m) and not m.promotion
            board.push(m)
            # Late move reduction on quiet moves searched late
            if i >= 4 and depth >= 3 and quiet and not in_check and not board.is_check():
                score = -self.negamax(board, depth - 2, -alpha - 1, -alpha, ply + 1)
                if score > alpha:
                    score = -self.negamax(board, depth - 1, -beta, -alpha, ply + 1)
            else:
                score = -self.negamax(board, depth - 1, -beta, -alpha, ply + 1)
            board.pop()

            if score > best:
                best, best_move = score, m
            if score > alpha:
                alpha = score
            if alpha >= beta:
                if quiet:
                    ks = self.killers.setdefault(ply, [])
                    if m not in ks:
                        ks.insert(0, m)
                        del ks[2:]
                    hk = (m.from_square, m.to_square)
                    self.history[hk] = self.history.get(hk, 0) + depth * depth
                break

        flag = 0 if orig_alpha < best < beta else (1 if best >= beta else -1)
        self.tt[key] = (depth, best, flag, best_move)
        return best

    def search_multipv(self, board, n, max_time=None, max_depth=64, info=None):
        """Iterative deepening with exact scores for the top n root moves.

        Returns [(move, score), ...] best first, scores from the side to move's view.
        """
        board = board.copy()  # TimeUp unwinds mid-search without popping moves
        self.deadline = time.monotonic() + max_time if max_time else None
        self.nodes = 0
        self.killers.clear()
        ranked = [(m, 0) for m in board.legal_moves]
        if not ranked:
            return []
        start = time.monotonic()
        for depth in range(1, max_depth + 1):
            scores = []
            try:
                for m, _ in ranked:  # previous depth's order: best first
                    # Exact score only matters if the move can enter the top n. Searching with alpha = current
                    # n-th best lets alpha-beta skip the rest; those scores are upper bounds and rank below.
                    top = sorted(s for _, s in scores)[-n:] if len(scores) >= n else None
                    alpha = top[0] if top else -INF
                    board.push(m)
                    score = -self.negamax(board, depth - 1, -INF, -alpha, 1)
                    board.pop()
                    scores.append((m, score))
            except TimeUp:
                break
            ranked = sorted(scores, key=lambda x: x[1], reverse=True)
            if info:
                info(depth, ranked[:n], self.nodes, max(time.monotonic() - start, 1e-3))
            if self.deadline and time.monotonic() > self.deadline:
                break
        return ranked[:n]

    @staticmethod
    def _has_pieces(board):
        us = board.turn
        return bool(board.occupied_co[us] & ~board.pawns & ~board.kings)

    def search(self, board, max_time=None, max_depth=64, info=None):
        """Iterative deepening. Returns the best move found."""
        board = board.copy()  # TimeUp unwinds mid-search without popping moves
        self.deadline = time.monotonic() + max_time if max_time else None
        self.nodes = 0
        self.killers.clear()
        if len(self.tt) > 2_000_000:
            self.tt.clear()
        best_move = next(iter(board.legal_moves), None)
        start = time.monotonic()
        for depth in range(1, max_depth + 1):
            try:
                score = self.negamax(board, depth, -INF, INF, 0)
            except TimeUp:
                break
            entry = self.tt.get(board._transposition_key())
            if entry and entry[3]:
                best_move = entry[3]
            if info:
                elapsed = max(time.monotonic() - start, 1e-3)
                info(depth, score, self.nodes, elapsed, best_move)
            if abs(score) > MATE - 1000:
                break
        return best_move
