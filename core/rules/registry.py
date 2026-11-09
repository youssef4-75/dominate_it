"""The list of all rules. THE place to add a new rule or to change the execution order."""
from __future__ import annotations

from typing import Dict, Tuple, Type

from core.rules.base import Rule
from core.rules.catch_up_cards import CatchUpCards
from core.rules.full_board_flip import FullBoardFlip
from core.rules.full_board_win import FullBoardWin
from core.rules.line_bonus import LineBonus
from core.rules.line_streak_wipe import LineStreakWipe

# EXECUTION ORDER of the after_move hooks. It matters: once a rule decides the move,
# the following ones are skipped. So: game-ending rules first, then penalties, then
# the bonus (a penalized move never gets a bonus).
RULES: Tuple[Type[Rule], ...] = (
    FullBoardWin,
    FullBoardFlip,
    LineStreakWipe,
    LineBonus,
    CatchUpCards,
)

BY_NAME: Dict[str, Type[Rule]] = {rule.name: rule for rule in RULES}
