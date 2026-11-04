# Grid Color War (console core)

Turn-based strategy game on a 5x5 grid. Each turn a random 3x3 card with 4
colored cells appears; the current player stamps it (its center goes on the
chosen cell) and the 4 cells overwrite the board. Completing a **new** full
line (row, column or diagonal) gives an extra move. The match lasts **50 turns
shared by both players** (bonus moves count). Most cells wins.

```
python main.py          # play (Python 3.9+, no dependencies)
pip install -r requirements-dev.txt && pytest
```
Input: `row col` (1-5), e.g. `3 4`. `q` quits to the home page.

## Layout

```
main.py             composition root: the ONLY file choosing concrete classes
application.py      glue: home page -> match -> replay/home loop
match_runner.py     glue: plays one match (Game + Renderer + MoveSelectors)
core/               pure game logic, depends on nothing
  models.py           Player, Position, MoveResult, Grid
  config.py           GameConfig (sizes, turns, diagonals...)
  board.py            Board: cells, painting, full lines
  card.py             Card, CardSource (interface), RandomCardSource
  game.py             Game: the rules
  errors.py           InvalidMoveError
players/            how a move is chosen
  base.py             MoveSelector (interface), MatchAborted
ui/                 how things are shown / how the user navigates
  base.py             Renderer + Menu (interfaces), menu choices
  messages.py         UI-independent texts shared by all renderers
  cmd/                console implementation
    ansi.py renderer.py menu.py human_player.py
tests/
```

### Dependency rule (arrows = "may import")

```
main -> application, match_runner -> ui.base, players.base -> core
ui/cmd -> ui.base, ui.messages, players.base -> core
```
`core` knows nothing about UI or players. `ui.cmd` is never imported by the
glue files, only by `main.py`.

## Extension points

| I want to...                         | I implement                              | I change         |
|--------------------------------------|------------------------------------------|------------------|
| draw with pyplot / tkinter / pygame  | `ui.Renderer` (+ `ui.Menu`) in `ui/<name>/` | `main.py` only   |
| decide moves with socket / NN / LLM  | `players.MoveSelector`                   | `main.py` only   |
| use another card distribution/deck   | `core.CardSource`                        | `main.py` only   |
| tweak rules (size, turns, diagonals) | `core.GameConfig`                        | `main.py` only   |

`MoveSelector.choose_move(game)` receives the whole `Game` as context
(`current_player`, `grid`, `current_card`, `turns_left`, `painted_cells(pos)`)
and returns a `Position`. Treat the game as read-only; only `MatchRunner`
calls `game.play()`.

```python
# players/my_bot.py
class MyBot(MoveSelector):
    def choose_move(self, game: Game) -> Position:
        ...  # query a model / a socket, then:
        return Position(row, col)
```
Mix freely in `main.py`, e.g. `selectors = {Player.RED: human, Player.BLUE: MyBot()}`.

Later, FastAPI/pygame split: `core` runs on the server, a `MoveSelector` backed
by a socket/HTTP client plays the remote side, and a pygame `Renderer` runs on
the client. No change to `core` is needed.

## Design decisions

* `Game` has no randomness or I/O of its own: cards come from an injected
  `CardSource`, so tests and replays are deterministic.
* `Game.grid` returns an immutable snapshot; the board cannot be mutated from outside.
* A selector that returns an invalid move makes `Game.play` raise
  `InvalidMoveError` (fail loudly). The console human re-prompts by itself.
* A line only gives a bonus if it is **newly** completed, and never on the last turn.
