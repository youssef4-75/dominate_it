from dataclasses import dataclass
from typing import List, Tuple

@dataclass
class MoveResult:
    player: str
    row: int
    col: int
    changed_cells: List[Tuple[int, int]]
    new_lines: List[str]  # human readable, e.g. "row 2", "column 4"
    bonus_turn: bool

