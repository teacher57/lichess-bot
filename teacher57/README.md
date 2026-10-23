# teacher57 engine

Classical chess engine in Python: alpha-beta search (iterative deepening, transposition table,
quiescence search, null-move pruning, late-move reductions, killer/history move ordering) plus a
tapered piece-square-table evaluation. Move generation comes from `python-chess`.

- `engine.py`: search and evaluation (also used by the bot's `!learn` mode to find its deliberate mistakes)
- `uci.py`: UCI front end (works with lichess-bot or any chess GUI), with `MultiPV` support for `!eval`

Thinking time is fixed: `THINK_TIME` at the top of `uci.py` (default 1.0 s per move). The game
clock is ignored, so only accept time controls where ~1 s/move fits (3+0 or slower).

Searches about 50k nodes/s, reaching depth 7 in ~1.5 s from the opening. Rough guess: ~1400–1700
on Lichess at blitz/rapid. It's weaker at bullet because Python is slow.

## Try it locally

```bash
printf 'uci\nposition startpos moves e2e4\ngo movetime 2000\nquit\n' | python teacher57/uci.py
```

## Ideas for v2
- Syzygy endgame tables
- Better eval: pawn structure, king safety, mobility
- Neural net trained on the Lichess database (Maia-style), or NNUE

## License

MIT, see [LICENSE](LICENSE). This covers the engine in this folder only. The rest of the repository is
lichess-bot, which is AGPL-3.0.
