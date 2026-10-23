#!/usr/bin/env python3
"""UCI front-end so lichess-bot (or any chess GUI) can talk to the engine."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import chess

from engine import MATE, Searcher

NAME = "teacher57-bot 0.1"

# Seconds spent thinking on every move. Fixed: clock, increment and `go` arguments are ignored.
THINK_TIME = 1.0


def uci_score(score):
    if abs(score) > MATE - 1000:
        plies = MATE - abs(score)
        return f"mate {(plies + 1) // 2 * (1 if score > 0 else -1)}"
    return f"cp {score}"


def main():
    board = chess.Board()
    searcher = Searcher()
    multipv = 1

    def out(line):
        print(line, flush=True)

    def info(depth, score, nodes, elapsed, move):
        out(f"info depth {depth} score {uci_score(score)} nodes {nodes} nps {int(nodes / elapsed)} "
            f"time {int(elapsed * 1000)} pv {move.uci()}")

    def info_multipv(depth, ranked, nodes, elapsed):
        for k, (move, score) in enumerate(ranked, 1):
            out(f"info depth {depth} multipv {k} score {uci_score(score)} nodes {nodes} "
                f"nps {int(nodes / elapsed)} time {int(elapsed * 1000)} pv {move.uci()}")

    for line in sys.stdin:
        tokens = line.split()
        if not tokens:
            continue
        cmd = tokens[0]
        if cmd == "uci":
            out(f"id name {NAME}")
            out("id author kenya")
            out("option name MultiPV type spin default 1 min 1 max 10")
            out("uciok")
        elif cmd == "isready":
            out("readyok")
        elif cmd == "ucinewgame":
            searcher = Searcher()
        elif cmd == "position":
            if tokens[1] == "startpos":
                board = chess.Board()
                rest = tokens[2:]
            else:  # position fen <6 fields> [moves ...]
                board = chess.Board(" ".join(tokens[2:8]))
                rest = tokens[8:]
            if rest and rest[0] == "moves":
                for mv in rest[1:]:
                    board.push_uci(mv)
        elif cmd == "setoption" and len(tokens) >= 5 and tokens[2].lower() == "multipv":
            multipv = max(1, min(10, int(tokens[4])))
        elif cmd == "go" and multipv > 1:
            # Analysis (e.g. !eval's top moves): honors `go movetime`, defaults to THINK_TIME.
            movetime = int(tokens[tokens.index("movetime") + 1]) / 1000 if "movetime" in tokens else THINK_TIME
            ranked = searcher.search_multipv(board, multipv, max_time=movetime, info=info_multipv)
            out(f"bestmove {ranked[0][0].uci() if ranked else '0000'}")
        elif cmd == "go":
            move = searcher.search(board, max_time=THINK_TIME, info=info)
            out(f"bestmove {move.uci() if move else '0000'}")
        elif cmd == "quit":
            break


if __name__ == "__main__":
    main()
