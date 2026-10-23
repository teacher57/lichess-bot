# teacher57-bot

A teaching chess bot for [Lichess](https://lichess.org): a small Python engine ([`teacher57/`](teacher57/)) running on a
customized fork of [lichess-bot](https://github.com/lichess-bot-devs/lichess-bot). AI friendly: built together with an AI
coding assistant.

## Chat commands (casual games)

| Command | What it does |
|---|---|
| `!line <moves>` | The bot follows your line, from move 1 or from the current position (`!line e4 e5 Nf3 Nc6 Bc4`, or `!line e6 d4 d5` after 1. e4). SAN or UCI, move numbers optional. If you leave the line, it plays its own moves. `!line` shows it, `!line off` cancels, `!line italian` works like `!opening italian`. |
| `!openings`, `!opening <name>` | Pick one of 13 named openings for the bot (Italian, Sicilian, French, ...). In casual games the bot waits 20 s before its first move so you can choose. |
| `!learn [chance %]` | Learning mode: after the opening the bot sometimes blunders on purpose, says "Oops!", and checks whether you find the punishment. `!learn off` stops it. |
| `!moretime [5-60]` | The bot adds seconds to your clock (15 by default). |
| `!eval` | Engine stats plus the top 3 moves. |

`!` starts a command and `/` ends it: anything after `/` is ignored, so you can repeat a command despite Lichess's
duplicate-message filter (`!moretime / 2`). Chatting before your first move also delays the bot's auto-abort.
Casual games also get unlimited takebacks.

## Setup

1. Install: `pip install -r requirements.txt`
2. Make a new Lichess account for the bot (no games played on it), create a token with the `bot:play` and
   `challenge:write` scopes, and upgrade it with `python lichess-bot.py -u`.
3. `cp config.yml.default config.yml`, then set `engine.dir: "./teacher57/"`, `engine.name: "uci.py"`,
   `engine.protocol: "uci"` and `engine.interpreter` to your Python.
4. Keep the token out of files: `export LICHESS_BOT_TOKEN=...` (lichess-bot reads it from the environment), then
   `python lichess-bot.py`.

## Contributors

- [teacher57](https://github.com/teacher57): author of teacher57-bot
- Claude (Anthropic's AI, via Claude Code): co-wrote the engine integration and the chat features (`!line`, `!learn`,
  `!moretime`, `!opening`)

Built on [lichess-bot](https://github.com/lichess-bot-devs/lichess-bot) by its contributors.

## License

Everything written for teacher57-bot is MIT ([LICENSE](teacher57/LICENSE)): the engine in [`teacher57/`](teacher57/),
plus [`lib/openings.py`](lib/openings.py) (`!opening`, `!line`) and [`lib/training.py`](lib/training.py) (`!learn`).
The rest is lichess-bot, including the edits wiring these features into its files, and stays under lichess-bot's
AGPL-3.0 ([LICENSE](LICENSE)), which only its authors could change. The bot as a whole is therefore distributed under
AGPL-3.0.

---

*The original lichess-bot README follows.*

<div align="center">

  ![lichess-bot](https://github.com/lichess-bot-devs/lichess-bot-images/blob/main/lichess-bot-icon-400.png)

  <h1>lichess-bot</h1>

  A bridge between [lichess.org](https://lichess.org) and bots.
  <br>
  <strong>[Explore lichess-bot docs »](https://github.com/lichess-bot-devs/lichess-bot/wiki)</strong>
  <br>
  <br>
  [![Python Build](https://github.com/lichess-bot-devs/lichess-bot/actions/workflows/python-build.yml/badge.svg)](https://github.com/lichess-bot-devs/lichess-bot/actions/workflows/python-build.yml)
  [![Python Test](https://github.com/lichess-bot-devs/lichess-bot/actions/workflows/python-test.yml/badge.svg)](https://github.com/lichess-bot-devs/lichess-bot/actions/workflows/python-test.yml)
  [![Mypy](https://github.com/lichess-bot-devs/lichess-bot/actions/workflows/mypy.yml/badge.svg)](https://github.com/lichess-bot-devs/lichess-bot/actions/workflows/mypy.yml)

</div>

## Overview

[lichess-bot](https://github.com/lichess-bot-devs/lichess-bot) is a free bridge
between the [Lichess Bot API](https://lichess.org/api#tag/Bot) and chess engines.

With lichess-bot, you can create and operate a bot on lichess. Your bot will be able to play against humans and bots alike, and you will be able to view these games live on lichess.

See also the lichess-bot [documentation](https://github.com/lichess-bot-devs/lichess-bot/wiki) for further usage help.

## Features
Supports:
- Every variant and time control
- UCI, XBoard, and Homemade engines
- Matchmaking (challenging other bots)
- Offering Draws and Resigning
- Participating in tournaments
- Accepting move takeback requests from opponents
- Saving games as PGN
- Local & Online Opening Books
- Local & Online Endgame Tablebases

Can run on:
- Python 3.10 and later
- Windows, Linux and MacOS
- Docker

## Steps
1. [Install lichess-bot](https://github.com/lichess-bot-devs/lichess-bot/wiki/How-to-Install)
2. [Create a lichess OAuth token](https://github.com/lichess-bot-devs/lichess-bot/wiki/How-to-create-a-Lichess-OAuth-token)
3. [Setup the engine](https://github.com/lichess-bot-devs/lichess-bot/wiki/Setup-the-engine)
4. [Configure lichess-bot](https://github.com/lichess-bot-devs/lichess-bot/wiki/Configure-lichess-bot)
5. [Upgrade to a BOT account](https://github.com/lichess-bot-devs/lichess-bot/wiki/Upgrade-to-a-BOT-account)
6. [Run lichess-bot](https://github.com/lichess-bot-devs/lichess-bot/wiki/How-to-Run-lichess%E2%80%90bot)

## Advanced options
- [Create a homemade engine](https://github.com/lichess-bot-devs/lichess-bot/wiki/Create-a-homemade-engine)
- [Add extra customizations](https://github.com/lichess-bot-devs/lichess-bot/wiki/Extra-customizations)

<br />

## Acknowledgements
Thanks to the Lichess team, especially T. Alexander Lystad and Thibault Duplessis for working with the LeelaChessZero team to get this API up. Thanks to [Niklas Fiekas](https://github.com/niklasf) and his [python-chess](https://github.com/niklasf/python-chess) code which allows engine communication seamlessly.

## License
lichess-bot is licensed under the AGPLv3 (or any later version at your option). Check out the [LICENSE file](https://github.com/lichess-bot-devs/lichess-bot/blob/master/LICENSE) for the full text.

## Citation
If this software has been used for research purposes, please cite it using the "Cite this repository" menu on the right sidebar. For more information, check the [CITATION file](https://github.com/lichess-bot-devs/lichess-bot/blob/master/CITATION.cff).
