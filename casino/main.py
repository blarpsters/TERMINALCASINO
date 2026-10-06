import shutil
from typing import Callable

from . import games
from .accounts import Account
from .config import Config
from .types import GameContext
from .utils import cprint, cinput, clear_screen, display_topbar, get_theme
from textual.app import App, ComposeResult
from textual.widgets import Footer, Header, Input, Static, Button
from textual.containers import VerticalScroll


CASINO_HEADER = """
┌──────────────────────────────────────┐
│   ♦ T E R M I N A L  C A S I N O ♦   │
└──────────────────────────────────────┘
"""

CASINO_HEADER_OPTIONS = {
    "header": CASINO_HEADER,
    "margin": 3,
}
ACCOUNT_STARTING_BALANCE = 100

ENTER_OR_QUIT_PROMPT = "[E]nter   [Q]uit: "
INVALID_CHOICE_PROMPT = "\nInvalid input. Please try again.\n"
GAME_CHOICE_PROMPT = "Please choose a game to play: "

# To add a new game, just add a handler function to GAME_HANDLERS

GAME_HANDLERS: dict[str, Callable[[GameContext], None]] = {
    "blackjack (U.S.)": games.blackjack.play_blackjack,
    "blackjack (E.U.)": games.blackjack.play_european_blackjack,
    "slots": games.slots.play_slots,
    "slots (Expanded)": games.slots.play_slots_expanded,
    "poker": games.poker.play_poker,
    "roulette": games.roulette.play_roulette,
    "uno": games.uno.play_uno,
    "european roulette": games.roulette.play_european_roulette,
}
ALL_GAMES = list(GAME_HANDLERS.keys())

def term_width() -> int:
    """Safe terminal width fallback."""
    try:
        return shutil.get_terminal_size().columns
    except Exception:
        return 80


def prompt_with_refresh(
    render_fn: Callable[[], None],
    prompt: str,
    error_message: str,
    validator: Callable[[str], bool],
    transform: Callable[[str], str] = lambda s: s.strip(),
) -> str:
    """
    Repeatedly render screen, show last error (if any), ask for input and validate.
    On EOF/KeyboardInterrupt return 'q' so caller can decide how to exit.
    """
    last_error = ""
    while True:
        render_fn()
        if last_error:
            cprint(last_error)
        answer = transform(cinput(prompt).strip())
        if validator(answer):
            return answer
        last_error = error_message


class CasinoPage(App[str]):
    """Shared layout for the Textual homepage and game selection."""

    TITLE = "Terminal Casino"
    BINDINGS = [("escape", "quit", "Quit")]
    CSS = """
    Screen { align: center top; }
    #body { width: 100%; max-width: 64; padding: 1 2; }
    #title {
        text-align: center;
        width: 100%;
        color: gold;
        text-style: bold;
        margin-bottom: 1;
    }
    #subtitle { text-align: center; margin-bottom: 1; }
    Input { margin-bottom: 1; }
    Button { width: 100%; margin-bottom: 1; }
    #error { color: $error; height: auto; margin-bottom: 1; }
    """


class NameSelect(CasinoPage):
    def compose(self) -> ComposeResult:
        yield Header()
        with VerticalScroll(id="body"):
            yield Static("♦ TERMINAL CASINO ♦", id="title")
            yield Static("Enter your name to start playing.", id="subtitle")
            yield Input(placeholder="Your name", id="name-input")
            yield Static("", id="error")
            yield Button("Enter Casino", variant="success", id="enter")
            yield Button("Quit", id="quit")
        yield Footer()

    def on_mount(self) -> None:
        self.query_one(Input).focus()

    def submit_name(self) -> None:
        name = self.query_one(Input).value.strip()
        if not name:
            self.query_one("#error", Static).update("Please enter your name.")
            self.query_one(Input).focus()
            return
        self.exit(name)

    def on_input_submitted(self, event: Input.Submitted) -> None:
        self.submit_name()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "enter":
            self.submit_name()
        elif event.button.id == "quit":
            self.exit()


class GameSelect(CasinoPage):
    def __init__(self, username: str, balance: int = ACCOUNT_STARTING_BALANCE):
        super().__init__()
        self.username = username
        self.balance = balance
        self.game_ids = {f"game-{i}": name for i, name in enumerate(ALL_GAMES)}

    def compose(self) -> ComposeResult:
        yield Header()
        with VerticalScroll(id="body"):
            yield Static("♦ TERMINAL CASINO ♦", id="title")
            yield Static(
                f"Welcome, {self.username}!\nBalance: {self.balance} | Choose a game",
                id="subtitle", markup=False,
            )
            for button_id, name in self.game_ids.items():
                yield Button(name.title(), id=button_id, variant="primary")
            yield Button("Quit Casino", id="quit")
        yield Footer()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "quit":
            self.exit()
        elif event.button.id in self.game_ids:
            self.exit(self.game_ids[event.button.id])


def main_menu(ctx: GameContext) -> None:
    """
    Main loop: show welcome, then (if chosen) show game menu, call handler,
    then return to top-level menu. No recursion used.
    """
    account = ctx.account
    while True:
        def render_welcome():
            clear_screen()
            display_topbar(account, **CASINO_HEADER_OPTIONS)
            cprint("")  # spacing

        action = prompt_with_refresh(
            render_fn = render_welcome,
            prompt = ENTER_OR_QUIT_PROMPT.center(term_width()),
            error_message = INVALID_CHOICE_PROMPT,
            validator = lambda x: x.lower() in {"e", "q"},
            transform = lambda s: s.strip().lower(),
        )

        if action == "q":
            clear_screen()
            display_topbar(account, **CASINO_HEADER_OPTIONS)
            cprint("\nGoodbye!\n")
            break  # exit loop -> program ends

        # --- choose game ---
        def render_choose_game():
            clear_screen()
            display_topbar(account, **CASINO_HEADER_OPTIONS)
            cprint("")  # spacing
            width = term_width()
            max_length = max(map(len, ALL_GAMES))
            cprint("┌" + "─" * 30 + "┐")
            cprint("│" + " " * 30 + "│")
            for i, name in enumerate(ALL_GAMES, start=1):
                cprint(
                    f"│{('[{}] {}'.format(i, name.title()) + ' ' * (max_length - len(name))).center(30)}│".center(width)
                )
            cprint("│" + " " * 30 + "│")
            cprint("└" + "─" * 30 + "┘")



        choice = prompt_with_refresh(
            render_fn = render_choose_game,
            prompt = GAME_CHOICE_PROMPT.center(term_width()),
            error_message = INVALID_CHOICE_PROMPT,
            validator = lambda x: x.isdigit() and 1 <= int(x) <= len(ALL_GAMES),
        )

        selected_game = ALL_GAMES[int(choice) - 1]
        handler = GAME_HANDLERS.get(selected_game)
        if handler:
            clear_screen()
            handler(ctx)  # returns to loop after game finishes
        else:
            clear_screen()
            display_topbar(account, **CASINO_HEADER_OPTIONS)
            cprint("\nNo such game!\n")


def main(name: str | None = None) -> None:
    """Run Textual menus, closing the UI before each legacy game starts."""
    name = name.strip() if name is not None else NameSelect().run()
    if not name:
        return

    ctx = GameContext(
        account=Account.generate(name, ACCOUNT_STARTING_BALANCE),
        config=Config.default(),
    )
    while True:
        selected_game = GameSelect(ctx.account.name, ctx.account.balance).run()
        if selected_game is None:
            break
        # App.run() has restored the terminal before the game uses input/print.
        clear_screen()
        GAME_HANDLERS[selected_game](ctx)

    clear_screen()
    cprint("\nGoodbye!\n")


if __name__ == "__main__":
    try:
        main()
    except (KeyboardInterrupt, EOFError):
        clear_screen()
        cprint("\nGoodbye! (Interrupted)\n")
