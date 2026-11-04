from typing import Tuple


class InputInterface:
  def select_move(self) -> Tuple[int, int]:
    ...