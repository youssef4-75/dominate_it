from typing import Set, Tuple

class GameInterface:
  def player_turn(self) -> str:
    ...

  def generate_card(self) -> Set[Tuple[int, int]]:
    ...

  def summary(self) -> dict:
    ...

  def moves_left(self) -> int:
    ...

  def 