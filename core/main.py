"""
GRID COLOR WAR - console core
=============================

Rules
-----
* The board is a 5x5 grid. Two players: RED and BLUE.
* Each turn a random 3x3 card appears. Exactly 4 of its 9 cells are colored
  with the current player's color.
* The player chooses a board cell. The CENTER of the card is placed on it, and
  the 4 colored card cells overwrite the board cells under them
  (parts of the card falling outside the board are simply ignored).
* If the move completes a NEW full line (row / column / diagonal) of the
  player's color, the player plays again.
* Colors can be overwritten again and again.
* Each player has 50 moves (a bonus move counts as one of them).
  When both have played all of them, the player with the most cells wins.
* Then players can replay or go back to the home menu.

Architecture
------------
* `Game`    -> pure game logic, NO input/output (reusable later by FastAPI).
* Console UI functions below -> printing / input only (to be replaced later
  by pygame on the frontend side).

Run:  python grid_game_core.py
"""

import os
import random
from dataclasses import dataclass, field
from typing import List, Optional, Set, Tuple

# --------------------------------------------------------------------------
# Settings
# --------------------------------------------------------------------------
BOARD_SIZE = 5
CARD_SIZE = 3
CARD_COLORED_CELLS = 4
TURNS_PER_PLAYER = 50
DIAGONALS_COUNT_AS_LINES = True

RED = "R"
BLUE = "B"
EMPTY = "."
PLAYERS = (RED, BLUE)
PLAYER_NAMES = {RED: "RED", BLUE: "BLUE"}


# --------------------------------------------------------------------------
# Game logic (no I/O)
# --------------------------------------------------------------------------
@dataclass
class MoveResult:
    player: str
    row: int
    col: int
    changed_cells: List[Tuple[int, int]]
    new_lines: List[str]  # human readable, e.g. "row 2", "column 4"
    bonus_turn: bool


@dataclass
class Game:
    size: int = BOARD_SIZE
    turns_per_player: int = TURNS_PER_PLAYER
    rng: random.Random = field(default_factory=random.Random)

    def __post_init__(self):
        self.board: List[List[str]] = [[EMPTY] * self.size for _ in range(self.size)]
        self.current: str = RED
        self.moves_played = {RED: 0, BLUE: 0}
        self.card: Set[Tuple[int, int]] = set()  # offsets (dr, dc) in -1..1
        self._draw_card()

    # ---- card -----------------------------------------------------------
    def _draw_card(self) -> None:
        """Pick 4 random cells out of the 3x3 card, stored as offsets from center."""
        half = CARD_SIZE // 2
        all_offsets = [(dr, dc) for dr in range(-half, half + 1)
                       for dc in range(-half, half + 1)]
        self.card = set(self.rng.sample(all_offsets, CARD_COLORED_CELLS))

    # ---- state queries --------------------------------------------------
    def moves_left(self, player: str) -> int:
        return self.turns_per_player - self.moves_played[player]

    def is_over(self) -> bool:
        return all(self.moves_left(p) <= 0 for p in PLAYERS)

    def scores(self) -> dict:
        return {p: sum(row.count(p) for row in self.board) for p in PLAYERS}

    def winner(self) -> Optional[str]:
        """Return RED / BLUE, or None for a draw."""
        s = self.scores()
        if s[RED] == s[BLUE]:
            return None
        return RED if s[RED] > s[BLUE] else BLUE

    def _lines(self):
        """Yield (label, [(r, c), ...]) for every line that counts."""
        n = self.size
        for r in range(n):
            yield f"row {r + 1}", [(r, c) for c in range(n)]
        for c in range(n):
            yield f"column {c + 1}", [(r, c) for r in range(n)]
        if DIAGONALS_COUNT_AS_LINES:
            yield "diagonal \\", [(i, i) for i in range(n)]
            yield "diagonal /", [(i, n - 1 - i) for i in range(n)]

    def full_lines(self, player: str) -> Set[str]:
        return {label for label, cells in self._lines()
                if all(self.board[r][c] == player for r, c in cells)}

    def card_cells_on_board(self, row: int, col: int) -> List[Tuple[int, int]]:
        """Board cells that the card would paint if centered on (row, col)."""
        cells = []
        for dr, dc in sorted(self.card):
            r, c = row + dr, col + dc
            if 0 <= r < self.size and 0 <= c < self.size:
                cells.append((r, c))
        return cells

    # ---- playing --------------------------------------------------------
    def play(self, row: int, col: int) -> MoveResult:
        """Play the current card centered on (row, col) (0-indexed)."""
        if self.is_over():
            raise ValueError("The game is over.")
        if not (0 <= row < self.size and 0 <= col < self.size):
            raise ValueError("Position is outside the board.")

        player = self.current
        lines_before = self.full_lines(player)

        painted = self.card_cells_on_board(row, col)
        changed = [(r, c) for r, c in painted if self.board[r][c] != player]
        for r, c in painted:
            self.board[r][c] = player

        new_lines = sorted(self.full_lines(player) - lines_before)
        self.moves_played[player] += 1

        bonus = bool(new_lines) and self.moves_left(player) > 0
        result = MoveResult(player, row, col, changed, new_lines, bonus)

        self._advance_turn(bonus)
        return result

    def _advance_turn(self, bonus: bool) -> None:
        if self.is_over():
            return
        me = self.current
        other = BLUE if me == RED else RED
        if bonus and self.moves_left(me) > 0:
            pass  # same player replays
        elif self.moves_left(other) > 0:
            self.current = other
        # else: the other has no moves left, current keeps playing
        self._draw_card()


# --------------------------------------------------------------------------
# Console UI (printing / input only)
# --------------------------------------------------------------------------
RESET = "\033[0m"
BOLD = "\033[1m"
BG = {RED: "\033[41m", BLUE: "\033[44m", EMPTY: "\033[100m"}
FG = {RED: "\033[91m", BLUE: "\033[94m"}
WHITE = "\033[97m"
DIM = "\033[90m"


def enable_ansi() -> None:
    if os.name == "nt":
        os.system("")  # enables ANSI escape codes in Windows terminals


def clear_screen() -> None:
    os.system("cls" if os.name == "nt" else "clear")


def colored(text: str, player: str) -> str:
    return f"{BOLD}{FG[player]}{text}{RESET}"


def cell_block(value: str, marker: bool = False, highlight: bool = False) -> str:
    """Two-character wide colored block."""
    text = "◆ " if marker else "  "
    if highlight:
        text = "▒▒"
    return f"{BG[value]}{WHITE}{text}{RESET}"


def render_board(game: Game, preview: Optional[Set[Tuple[int, int]]] = None) -> str:
    preview = preview or set()
    lines = ["     " + " ".join(f" {c + 1}" for c in range(game.size))]
    for r in range(game.size):
        row_txt = f"  {r + 1}  "
        row_txt += " ".join(
            cell_block(game.board[r][c], highlight=(r, c) in preview)
            for c in range(game.size)
        )
        lines.append(row_txt)
    return "\n".join(lines)


def render_card(game: Game) -> str:
    half = CARD_SIZE // 2
    lines = []
    for dr in range(-half, half + 1):
        parts = []
        for dc in range(-half, half + 1):
            value = game.current if (dr, dc) in game.card else EMPTY
            parts.append(cell_block(value, marker=(dr == 0 and dc == 0)))
        lines.append("      " + " ".join(parts))
    return "\n".join(lines)


def show_screen(game: Game, message: str = "") -> None:
    clear_screen()
    s = game.scores()
    print(f"{BOLD}=== GRID COLOR WAR ==={RESET}\n")
    print(f"  {colored('RED', RED)}: {s[RED]:>2} cells  ({game.moves_left(RED)} moves left)")
    print(f"  {colored('BLUE', BLUE)}: {s[BLUE]:>2} cells  ({game.moves_left(BLUE)} moves left)\n")
    print(render_board(game))
    print()
    if message:
        print(message + "\n")
    if not game.is_over():
        print(f"  {colored(PLAYER_NAMES[game.current], game.current)}'s card "
              f"(◆ = center, placed on the cell you choose):\n")
        print(render_card(game))
        print()


def ask_move(game: Game) -> Optional[Tuple[int, int]]:
    """Ask the current player for a cell. Returns (row, col) 0-indexed, or None to quit."""
    player = game.current
    prompt = (f"{colored(PLAYER_NAMES[player], player)} - choose a cell "
              f"as 'row col' (1-{game.size}), or 'q' to quit: ")
    while True:
        raw = input(prompt).strip().lower()
        if raw in ("q", "quit", "exit"):
            return None
        parts = raw.replace(",", " ").split()
        if len(parts) == 2 and all(p.isdigit() for p in parts):
            row, col = int(parts[0]) - 1, int(parts[1]) - 1
            if 0 <= row < game.size and 0 <= col < game.size:
                return row, col
        print(f"  {DIM}Invalid input. Example: 3 4  (row 3, column 4){RESET}")


def describe_result(result: MoveResult) -> str:
    name = colored(PLAYER_NAMES[result.player], result.player)
    msg = (f"{name} played at row {result.row + 1}, col {result.col + 1} "
           f"({len(result.changed_cells)} cell(s) changed).")
    if result.new_lines:
        msg += f"\n  Full line completed: {', '.join(result.new_lines)}!"
    if result.bonus_turn:
        msg += f"\n  {colored(PLAYER_NAMES[result.player], result.player)} plays again!"
    return msg


def play_match() -> bool:
    """Play one full match. Returns False if a player quit mid-game."""
    game = Game()
    message = "Game start! RED begins."
    while not game.is_over():
        show_screen(game, message)
        move = ask_move(game)
        if move is None:
            return False
        result = game.play(*move)
        message = describe_result(result)

    show_screen(game, message)
    s = game.scores()
    print(f"{BOLD}=== GAME OVER ==={RESET}")
    print(f"  {colored('RED', RED)}: {s[RED]}   {colored('BLUE', BLUE)}: {s[BLUE]}")
    w = game.winner()
    if w is None:
        print(f"\n  {BOLD}It's a draw!{RESET}\n")
    else:
        print(f"\n  {BOLD}{colored(PLAYER_NAMES[w], w)} {BOLD}wins!{RESET}\n")
    return True


def main_menu() -> None:
    enable_ansi()
    while True:
        clear_screen()
        print(f"{BOLD}=== GRID COLOR WAR ==={RESET}\n")
        print("  1) Play")
        print("  2) Quit\n")
        choice = input("Choice: ").strip()
        if choice == "1":
            while True:
                finished = play_match()
                if not finished:
                    break  # quit mid-game -> home page
                again = input("Replay (r) or go back to home page (h)? ").strip().lower()
                if again != "r":
                    break
        elif choice == "2":
            print("Bye!")
            return


if __name__ == "__main__":
    main_menu()