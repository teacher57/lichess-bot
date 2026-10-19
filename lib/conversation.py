"""Allows lichess-bot to send messages to the chat."""
import logging
import chess
import chess.engine
from lib import model, openings, training
from lib.engine_wrapper import EngineWrapper
from lib.lichess import Lichess, MAX_CHAT_MESSAGE_LEN
from lib.lichess_types import GameEventType
from collections.abc import Sequence
from lib.timer import seconds
from typing import TypeAlias, cast
MULTIPROCESSING_LIST_TYPE: TypeAlias = Sequence[model.Challenge]

logger = logging.getLogger(__name__)

# Seconds the opponent gets for their first move after chatting, before the bot aborts the game.
CHAT_ABORT_DELAY = 60

# !moretime: seconds added to the opponent's clock (lichess allows 5-60 per call).
MORETIME_DEFAULT = 15
MORETIME_MIN = 5
MORETIME_MAX = 60


class ChatLine:
    """Information about the message."""

    def __init__(self, message_info: GameEventType) -> None:
        """Information about the message."""
        self.room = message_info["room"]
        """Whether the message was sent in the chat room or in the spectator room."""
        self.username = message_info["username"]
        """The username of the account that sent the message."""
        self.text = message_info["text"]
        """The message sent."""


class Conversation:
    """Enables the bot to communicate with its opponent and the spectators."""

    def __init__(self, game: model.Game, engine: EngineWrapper, li: Lichess, version: str,
                 challenge_queue: MULTIPROCESSING_LIST_TYPE) -> None:
        """
        Communication between lichess-bot and the game chats.

        :param game: The game that the bot will send messages to.
        :param engine: The engine playing the game.
        :param li: A class that is used for communication with lichess.
        :param version: The lichess-bot version.
        :param challenge_queue: The active challenges the bot has.
        """
        self.game = game
        self.engine = engine
        self.li = li
        self.version = version
        self.challengers = challenge_queue
        self.messages: list[ChatLine] = []

    command_prefix = "!"

    def react(self, line: ChatLine) -> None:
        """
        React to a received message.

        :param line: Information about the message.
        """
        self.messages.append(line)
        logger.info(f"*** {self.game.url()} [{line.room}] {line.username}: {line.text}")
        if line.room == "player" and line.username != self.game.username:
            # The opponent is here (e.g. typing a !line), so give them time for their first move.
            self.game.delay_abort(seconds(CHAT_ABORT_DELAY))
        if line.text[0] == self.command_prefix:
            self.command(line, line.text[1:].lower())

    def command(self, line: ChatLine, cmd: str) -> None:
        """
        Reacts to the specific commands in the chat.

        :param line: Information about the message.
        :param cmd: The command to react to.
        """
        from_self = line.username == self.game.username
        is_eval = cmd.startswith("eval")
        if cmd in ("commands", "help"):
            self.send_reply(line,
                            "Supported commands: !wait (wait a minute for my first move), !name, "
                            "!eval (or any text starting with !eval; casual games only), !queue, "
                            "!openings (openings you can pick for me; casual games only), "
                            "!opening <name> (pick one), !opening off (cancel), "
                            "!line <moves> (I follow your line, from move 1 or from the current position, e.g. !line e4 e5 Nf3 Nc6 Bc4; "
                            "if you leave it, I play my own moves; casual only), !line (show it), !line off, "
                            "!learn [chance %] (I blunder sometimes, find the tactic; casual only), !learn off, "
                            f"!moretime [{MORETIME_MIN}-{MORETIME_MAX}] (I add seconds to your clock, "
                            f"{MORETIME_DEFAULT} by default; casual only)")
        elif cmd == "openings" or cmd.startswith("opening "):
            self.opening_command(line, cmd)
        elif cmd == "moretime" or cmd.startswith("moretime "):
            self.moretime_command(line, cmd)
        elif cmd == "line" or cmd.startswith("line "):
            self.line_command(line, line.text[len(self.command_prefix) + len("line"):].strip())
        elif cmd == "learn" or cmd.startswith("learn "):
            self.learn_command(line, cmd)
        elif cmd == "wait" and self.game.is_abortable():
            self.game.ping(seconds(60), seconds(120), seconds(120))
            self.send_reply(line, "Waiting 60 seconds...")
        elif cmd == "name":
            name = self.game.me.name
            self.send_reply(line, f"{name} running {self.engine.name()} (lichess-bot v{self.version})")
        elif is_eval and (from_self or line.room == "spectator" or self.game.mode == "casual"):
            stats = self.engine.get_stats(for_chat=True)
            self.send_reply(line, ", ".join(stats))
            self.send_top_moves(line)
        elif is_eval:
            self.send_reply(line, "I don't tell that to my opponent, sorry.")
        elif cmd == "queue":
            if self.challengers:
                challengers = ", ".join([f"@{challenger.challenger.name}" for challenger in reversed(self.challengers)])
                self.send_reply(line, f"Challenge queue: {challengers}")
            else:
                self.send_reply(line, "No challenges queued.")

    def send_top_moves(self, line: ChatLine, count: int = 3, think_seconds: float = 1.0) -> None:
        """Analyse the current position and reply with the top moves, best first, scores from White's view."""
        board = chess.Board()
        for move in self.game.state.get("moves", "").split():
            board.push_uci(move)
        if board.is_game_over() or not isinstance(self.engine.engine, chess.engine.SimpleEngine):
            return
        infos = self.engine.engine.analyse(board, chess.engine.Limit(time=think_seconds), multipv=count)
        tops = []
        for info in infos:
            if not info.get("pv"):
                continue
            score = info["score"].white()
            shown = f"#{score.mate()}" if score.is_mate() else f"{cast(int, score.score()) / 100:+.2f}"
            tops.append(f"{board.san(info['pv'][0])} {shown}")
        if tops:
            self.send_reply(line, "Top moves: " + ", ".join(tops))

    def learn_command(self, line: ChatLine, cmd: str) -> None:
        """Handle !learn and !learn off from the players (casual games only, until her 5th move)."""
        if line.room != "player":
            return
        if self.game.mode != "casual":
            self.send_reply(line, "Learning mode works in casual games only.")
            return
        if cmd == "learn off":
            training.sessions.pop(self.game.id, None)
            self.send_reply(line, "Learning mode off.")
            return
        board = chess.Board()
        for move in self.game.state.get("moves", "").split():
            board.push_uci(move)
        if training.her_moves_made(board, self.game.is_white) >= training.LEARN_UNTIL_MOVE:
            self.send_reply(line, f"Learning mode has to be turned on before my move {training.LEARN_UNTIL_MOVE}.")
            return
        arg = cmd.split(maxsplit=1)[1].strip().rstrip("%") if " " in cmd else str(training.DEFAULT_CHANCE)
        if not arg.isdigit() or not 1 <= int(arg) <= 100:
            self.send_reply(line, "Type !learn or !learn <chance 1-100>, e.g. !learn 30")
            return
        training.sessions.setdefault(self.game.id, training.Session()).chance = int(arg)
        self.send_reply(line, f"Learning mode on ({arg}%): after the opening I'll sometimes blunder and say Oops! "
                              "Find the winning line (2-3 moves).")

    def opening_command(self, line: ChatLine, cmd: str) -> None:
        """Handle !openings and !opening <name>/off from the players (casual games only)."""
        if line.room != "player":
            return
        if self.game.mode != "casual":
            self.send_reply(line, "Picking my opening works in casual games only.")
            return
        bot_color = chess.WHITE if self.game.is_white else chess.BLACK
        moves = self.game.state.get("moves", "").split()
        available = openings.possible(bot_color, moves)
        if cmd == "openings":
            if available:
                self.send_reply(line, "Type !opening <name>: " + ", ".join(available))
            else:
                self.send_reply(line, "No openings can be picked from this position.")
            return
        choice = cmd.split(maxsplit=1)[1].strip()
        if choice == "off":
            openings.chosen_by_game.pop(self.game.id, None)
            self.send_reply(line, "OK, I'll pick my own moves.")
        elif choice in available:
            openings.choose(self.game.id, choice)
            self.send_reply(line, f"OK, I'll play the {openings.name(choice)}.")
        elif choice in openings.OPENINGS:
            self.send_reply(line, f"The {openings.name(choice)} isn't possible from here. Type !openings to see what is.")
        else:
            self.send_reply(line, f"I don't know '{choice}'. Type !openings to see the list.")

    def moretime_command(self, line: ChatLine, cmd: str) -> None:
        """Handle !moretime [seconds] from the opponent: add time to their clock (casual games only)."""
        if line.room != "player" or line.username == self.game.username:
            return
        if self.game.mode != "casual":
            self.send_reply(line, "Extra time works in casual games only.")
            return
        arg = cmd.split(maxsplit=1)[1].strip().rstrip("s") if " " in cmd else str(MORETIME_DEFAULT)
        if not arg.isdigit() or not MORETIME_MIN <= int(arg) <= MORETIME_MAX:
            self.send_reply(line, f"Type !moretime or !moretime <{MORETIME_MIN}-{MORETIME_MAX} seconds>, e.g. !moretime 30")
            return
        if self.li.add_time(self.game.id, int(arg)):
            self.send_reply(line, f"Added {arg} s to your clock. Take your time!")
        else:
            self.send_reply(line, "Lichess didn't let me add time right now, sorry.")

    def line_command(self, line: ChatLine, moves_text: str) -> None:
        """Handle !line <moves>, !line and !line off from the players (casual games only)."""
        if line.room != "player":
            return
        if self.game.mode != "casual":
            self.send_reply(line, "Setting my line works in casual games only.")
            return
        if not moves_text:
            chosen = openings.chosen_by_game.get(self.game.id)
            self.send_reply(line, f"I'm following: {openings.describe(chosen[1])}" if chosen
                            else "No line set. Type !line <moves>, e.g. !line e4 e5 Nf3 Nc6 Bc4")
            return
        if moves_text.lower() == "off":
            openings.chosen_by_game.pop(self.game.id, None)
            self.send_reply(line, "OK, I'll pick my own moves.")
            return
        try:
            played = self.game.state.get("moves", "").split()
            custom = openings.parse_line(moves_text, played)
        except ValueError as error:
            self.send_reply(line, str(error))
            return
        bot_color = chess.WHITE if self.game.is_white else chess.BLACK
        problem = openings.set_line(self.game.id, bot_color, played, custom)
        self.send_reply(line, problem or f"OK, I'll follow your line: {openings.describe(custom)}")

    def send_reply(self, line: ChatLine, reply: str) -> None:
        """
        Send the reply to the chat.

        :param line: Information about the original message that we reply to.
        :param reply: The reply to send.
        """
        # Lichess drops chat messages over MAX_CHAT_MESSAGE_LEN, so send long replies in pieces split at spaces.
        chunks = [""]
        for word in reply.split(" "):
            if chunks[-1] and len(chunks[-1]) + 1 + len(word) > MAX_CHAT_MESSAGE_LEN:
                chunks.append("")
            chunks[-1] = f"{chunks[-1]} {word}" if chunks[-1] else word
        for chunk in chunks:
            logger.info(f"*** {self.game.url()} [{line.room}] {self.game.username}: {chunk}")
            self.li.chat(self.game.id, line.room, chunk)

    def send_message(self, room: str, message: str) -> None:
        """Send the message to the chat."""
        if message:
            self.send_reply(ChatLine({"room": room, "username": "", "text": ""}), message)
