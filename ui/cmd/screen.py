import os
from typing import Optional, Set, Tuple
from .vars import *
from core import Game, MoveResult, CARD_SIZE, FIRST_PLAYER, SECOND_PLAYER, EMPTY, PLAYER_NAMES
 
class Screen:
    """Everything the console shows or reads. No game rules live here."""
 
    TITLE = "=== GRID COLOR WAR ==="
 
    def __init__(self) -> None:
        self.enable_ansi()
 
    # ------------------------------------------------------------------
    # Terminal helpers
    # ------------------------------------------------------------------
    @staticmethod
    def enable_ansi() -> None:
        if os.name == "nt":
            os.system("")  # enables ANSI escape codes in Windows terminals
 
    @staticmethod
    def clear() -> None:
        os.system("cls" if os.name == "nt" else "clear")
 
    @staticmethod
    def colored(text: str, player: str) -> str:
        return f"{BOLD}{FG[player]}{text}{RESET}"
 
    def player_label(self, player: str) -> str:
        return self.colored(PLAYER_NAMES[player], player)
 
    # ------------------------------------------------------------------
    # Rendering (return strings)
    # ------------------------------------------------------------------
    @staticmethod
    def cell_block(value: str, marker: bool = False, highlight: bool = False) -> str:
        """Two-character wide colored block."""
        text = "◆ " if marker else "  "
        if highlight:
            text = "▒▒"
        return f"{BG[value]}{WHITE}{text}{RESET}"
 
    def render_board(self, game: Game, preview: Optional[Set[Tuple[int, int]]] = None) -> str:
        preview = preview or set()
        lines = ["     " + " ".join(f" {c + 1}" for c in range(game.size))]
        for r in range(game.size):
            row_txt = f"  {r + 1}  "
            row_txt += " ".join(
                self.cell_block(game.board[r][c], highlight=(r, c) in preview)
                for c in range(game.size)
            )
            lines.append(row_txt)
        return "\n".join(lines)
 
    def render_card(self, game: Game) -> str:
        half = CARD_SIZE // 2
        lines = []
        for dr in range(-half, half + 1):
            parts = []
            for dc in range(-half, half + 1):
                value = game.current if (dr, dc) in game.card else EMPTY
                parts.append(self.cell_block(value, marker=(dr == 0 and dc == 0)))
            lines.append("      " + " ".join(parts))
        return "\n".join(lines)
 
    def format_result(self, result: MoveResult) -> str:
        """Turn a MoveResult into a message to display."""
        name = self.player_label(result.player)
        msg = (f"{name} played at row {result.row + 1}, col {result.col + 1} "
               f"({len(result.changed_cells)} cell(s) changed).")
        if result.new_lines:
            msg += f"\n  Full line completed: {', '.join(result.new_lines)}!"
        if result.bonus_turn:
            msg += f"\n  {name} plays again!"
        return msg
 
    # ------------------------------------------------------------------
    # Output (print screens)
    # ------------------------------------------------------------------
    def show_menu(self) -> None:
        self.clear()
        print(f"{BOLD}{self.TITLE}{RESET}\n")
        print("  1) Play")
        print("  2) Quit\n")
 
    def show_game(self, game: Game, message: str = "") -> None:
        self.clear()
        s = game.scores()
        print(f"{BOLD}{self.TITLE}{RESET}\n")
        for p in (FIRST_PLAYER, SECOND_PLAYER):
            print(f"  {self.player_label(p)}: {s[p]:>2} cells  ({game.moves_left(p)} moves left)")
        print()
        print(self.render_board(game))
        print()
        if message:
            print(message + "\n")
        if not game.is_over():
            print(f"  {self.player_label(game.current)}'s card "
                  f"(◆ = center, placed on the cell you choose):\n")
            print(self.render_card(game))
            print()
 
    def show_game_over(self, game: Game) -> None:
        s = game.scores()
        print(f"{BOLD}=== GAME OVER ==={RESET}")
        print(f"  {self.player_label(FIRST_PLAYER)}: {s[FIRST_PLAYER]}   "
              f"{self.player_label(SECOND_PLAYER)}: {s[SECOND_PLAYER]}")
        w = game.winner()
        if w is None:
            print(f"\n  {BOLD}It's a draw!{RESET}\n")
        else:
            print(f"\n  {self.player_label(w)} {BOLD}wins!{RESET}\n")
 
    @staticmethod
    def show_message(message: str) -> None:
        print(message)
 
    # ------------------------------------------------------------------
    # Input
    # ------------------------------------------------------------------
    @staticmethod
    def ask_menu_choice() -> str:
        return input("Choice: ").strip()
 
    def ask_move(self, game: Game) -> Optional[Tuple[int, int]]:
        """Ask the current player for a cell. Returns (row, col) 0-indexed, or None to quit."""
        prompt = (f"{self.player_label(game.current)} - choose a cell "
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
 
    @staticmethod
    def ask_replay() -> bool:
        """True = replay, False = back to home page."""
        answer = input("Replay (r) or go back to home page (h)? ").strip().lower()
        return answer == "r"
 