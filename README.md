# Grid Color War

Turn-based strategy game on a 5x5 grid for two players (RED and BLUE).

* Each turn a random 3x3 card appears with 4 cells colored in the current player's color.
* The player picks a board cell: the card's **center** goes there and its 4 colored
  cells **overwrite** the board (parts outside the board are ignored).
* Completing a **new** full line (row, column or diagonal) gives an extra move.
* The match lasts **50 turns shared by both players** (bonus moves count).
  The player with the most cells wins. Then: replay or back to the home page.

## Run

```bash
pip install -r requirements.txt     # pygame (only needed for the window UI)
python main.py                      # pygame window (default)
python main.py --ui cmd             # console version, no dependencies

pip install -r requirements-dev.txt && pytest     # run the tests
```

**pygame:** click a cell (a translucent preview shows where the card will paint).
`Esc` quits to the home page; closing the window exits. Menus: Enter/1 Play,
Esc/2 Quit, R Replay, H Home.
**console:** type `row col` (1-5), e.g. `3 4`; `q` quits to the home page.

---

## 1. Project map

```
main.py             composition root: picks the UI and the players (the ONLY file that does)
application.py      home page -> match -> replay/home loop
match_runner.py     plays ONE match: render -> ask move -> play -> repeat

core/               the game itself; imports nothing from the rest of the project
  models.py           Player, Position, MoveResult, Grid
  config.py           GameConfig: board size, turns, card size, diagonals...
  board.py            Board: cells, painting, "full line" detection
  card.py             Card, CardSource (interface), RandomCardSource
  game.py             Game: the rules (play, turns, bonus, winner)
  errors.py           InvalidMoveError

players/            HOW A MOVE IS CHOSEN
  base.py             MoveSelector (interface), MatchAborted

ui/                 HOW THINGS ARE SHOWN
  base.py             Renderer + Menu (interfaces), MainChoice / AfterMatchChoice
  messages.py         texts shared by every UI ("X played at row...", "X wins!")
  cmd/                console implementation
    ansi.py             colors, block characters, clear screen
    renderer.py         draws the board/scores/card as text
    menu.py             home page + replay question
    human_player.py     reads "row col" from the keyboard
  pygame_ui/          pygame implementation
    window.py           the window, clock, event queue (shared by the 3 classes below)
    theme.py            window size, colors, fonts
    layout.py           where things are + pixel -> cell mapping
    drawing.py          drawing functions + Button
    renderer.py         draws a frame
    menu.py             home page + replay buttons
    human_player.py     mouse click -> move

tests/              pytest; one file per area (see section 6)
```

**Dependency rule** (arrows = "may import"):

```
main -> application, match_runner -> ui.base, players.base -> core
ui/cmd, ui/pygame_ui -> ui.base, ui.messages, players.base -> core
```
`core` knows nothing about UI or players. The glue files never import `ui/cmd` or
`ui/pygame_ui`: only `main.py` does.

**One turn, step by step** (`match_runner.py`):
`renderer.render_game(game, last_move)` -> `selector.choose_move(game)` ->
`game.play(position)` -> loop until `game.is_over` -> `render_game_over`.

---

## 2. "I want to change X" -> which file

### Game rules and settings

| I want to change...                         | Edit | Exactly what |
|---------------------------------------------|------|--------------|
| board size, number of turns, card size, colored cells per card, diagonals on/off, who starts | `core/config.py` | the default values of `GameConfig`. Or leave defaults and pass your own in `main.py`: `build_application(config=GameConfig(total_turns=20), ui=args.ui)` |
| what counts as a "full line" (e.g. only rows, longer lines) | `core/board.py` | `Board._lines()` (it yields every line as a label + list of positions) |
| when the bonus turn is granted / the bonus rule | `core/game.py` | `Game.play()`, the line `bonus = bool(new_lines) and not self.is_over` |
| how turns pass / who plays next             | `core/game.py` | `Game._advance()` |
| what happens at the board edges (card clipped) | `core/game.py` | `Game.painted_cells()` |
| how cards are generated (shape, number of cells, a fixed deck, same cards for both players...) | `core/card.py` | `RandomCardSource.next_card()`, or write a new `CardSource` class and use it in `main.py` (`new_game()`) |
| how the winner is decided / how scores are counted | `core/game.py` | `Game.winner()` and `Game.scores()` (cell counting is `Board.count()` in `core/board.py`) |
| when the game ends                          | `core/game.py` | `Game.is_over` (and `GameConfig.total_turns`) |
| what is stored about a move (for replays, logs, network) | `core/models.py` | `MoveResult`, filled in at the end of `Game.play()` |
| the two players / their identifiers         | `core/models.py` | `Player` enum. (A 3rd player is possible but touches many files: score boxes, colors, turn order.) |

### Who plays (humans, bots, network, neural network, LLM)

| I want to...                                  | Edit |
|-----------------------------------------------|------|
| make BLUE a bot, or RED a network player      | `main.py`: the `selectors = {Player.RED: ..., Player.BLUE: ...}` line in `build_application()` |
| write a new kind of player                    | new file in `players/` implementing `MoveSelector.choose_move(game) -> Position` (see section 3) |
| change how a human clicks / types their move  | `ui/pygame_ui/human_player.py` or `ui/cmd/human_player.py` |
| change what a player can see about the game   | nothing to edit: a selector gets the whole `Game` (`current_player`, `grid`, `current_card`, `turns_left`, `painted_cells(position)`, `scores()`) |

### pygame look and behavior

| I want to change...                           | Edit | Exactly what |
|-----------------------------------------------|------|--------------|
| window size, all colors, font sizes           | `ui/pygame_ui/theme.py` | `WINDOW_SIZE`, the color constants, `PLAYER_COLORS`, `Fonts.create()` |
| window title, frame rate                      | `ui/pygame_ui/window.py` | the `title` and `fps` parameters of `PygameWindow.__init__` |
| board position/size, gap between cells, card preview position/size | `ui/pygame_ui/layout.py` | class constants `GAP`, `BOARD_TOP`, `BOARD_AREA`, `CARD_CELL`, `CARD_GAP`, `CARD_ORIGIN` |
| rounded corners, how cells/board/card are drawn | `ui/pygame_ui/drawing.py` | `CELL_RADIUS`, `_draw_board()`, `_draw_card()` |
| the score boxes, "Turns left", the title      | `ui/pygame_ui/drawing.py` | `_draw_scores()` and `draw_scene()` |
| the hover preview (color, opacity, outline)   | `ui/pygame_ui/drawing.py` | `draw_preview()` |
| the GAME OVER overlay                         | `ui/pygame_ui/drawing.py` | `draw_game_over()` |
| the hint text at the bottom, the message under the board | `ui/pygame_ui/drawing.py` | end of `draw_scene()` |
| home page: title, buttons, labels, positions, keyboard shortcuts | `ui/pygame_ui/menu.py` | `main_menu_buttons()`, `after_match_buttons()`, `ask_main_choice()`, the `keys` dictionaries |
| button look (colors, border)                  | `ui/pygame_ui/drawing.py` (`Button.draw`) and `theme.py` (`BUTTON`, `BUTTON_HOVER`) |
| mouse/keyboard behavior during a match (e.g. right click, Esc) | `ui/pygame_ui/human_player.py` | `PygameHumanPlayer.choose_move()` |

Limits to know: the card preview area (bottom-left) is sized for a **3x3** card; a
bigger `card_size` needs a bigger `WINDOW_SIZE` height and `Layout.CARD_ORIGIN`.
Any board size works: cell size is computed from `Layout.BOARD_AREA`.

### Console look and behavior

| I want to change...                           | Edit | Exactly what |
|-----------------------------------------------|------|--------------|
| colors, block characters, clear screen        | `ui/cmd/ansi.py` | `_FG`, `_BG`, `_BG_EMPTY`, `cell_block()` |
| what is printed each turn (header, scores, board, card) | `ui/cmd/renderer.py` | `CmdRenderer.render_game()`, `_board_text()`, `_card_text()` |
| the game over screen                          | `ui/cmd/renderer.py` | `CmdRenderer.render_game_over()` |
| the accepted input format / quit words        | `ui/cmd/human_player.py` | `parse_position()`, `QUIT_WORDS`, the prompt in `choose_move()` |
| home page and replay question                 | `ui/cmd/menu.py` | `ask_main_choice()`, `ask_after_match()` |

### Texts and flow

| I want to change...                           | Edit | Exactly what |
|-----------------------------------------------|------|--------------|
| the wording of "X played at row...", "plays again", "wins" (all UIs) | `ui/messages.py` | `describe_start()`, `describe_move()`, `describe_outcome()` |
| the order of a match (e.g. pause after each move, log moves, record a replay) | `match_runner.py` | `MatchRunner.run()` |
| the home page flow (e.g. add a "settings" screen, ask names) | `application.py` and the `MainChoice` enum in `ui/base.py`, then the menus in `ui/cmd/menu.py` / `ui/pygame_ui/menu.py` |
| which UI starts by default                    | `main.py`: `DEFAULT_UI` |

---

## 3. Recipes

### Add a bot (or a socket / neural network / LLM player)

```python
# players/random_bot.py
import random
from core import Game, Position
from players import MoveSelector

class RandomBot(MoveSelector):
    def choose_move(self, game: Game) -> Position:
        # `game` is the whole context. Read it, decide, return a position.
        # Never call game.play() yourself: the MatchRunner does.
        return Position(random.randrange(game.size), random.randrange(game.size))
```
Then in `main.py` (`build_application`):

```python
from players.random_bot import RandomBot
selectors = {Player.RED: human, Player.BLUE: RandomBot()}
```
A selector may `raise MatchAborted` to abandon the match. If it returns an
invalid position, `Game.play` raises `InvalidMoveError`.
A neural network / LLM / socket player is the same class: build its input from
`game.grid`, `game.current_card.offsets`, `game.current_player`, `game.turns_left`.

### Add a new interface (tkinter, pyplot, web...)

1. Create `ui/my_ui/` with three classes: a `Renderer`, a `Menu` (both from
   `ui/base.py`) and a human `MoveSelector` (from `players/base.py`).
   Use `ui/messages.py` for texts. Copy the structure of `ui/pygame_ui/`.
2. In `main.py`: add a branch in `_build_ui()` and add the name to `UI_CHOICES`.
3. Nothing else changes (`core`, `match_runner.py`, `application.py` stay as they are).

### Change the rules of cards

Write a class implementing `CardSource.next_card() -> Card` (see `core/card.py`),
for example a fixed deck or cards shared with a remote server, and return it from
`new_game()` in `main.py`.

---

## 4. How the pygame UI fits the synchronous interfaces

The interfaces are plain blocking calls, so pygame needs no special architecture:
`PygameRenderer` draws and flips; `PygameHumanPlayer.choose_move` and
`PygameMenu.ask_*` run their own small event loops until the user decides. The 3
classes share one `PygameWindow`. When the user closes the window,
`window.closed` becomes True: the human player raises `MatchAborted`, the menu
answers Quit/Home, and `Menu.show_goodbye()` releases pygame.

Known limit: closing the window is only noticed while waiting for a human or a
menu. A slow bot that thinks for seconds would freeze the window; run it in a
thread or call `window.pump()` while it thinks.

## 5. Design decisions

* `Game` has no randomness or I/O of its own: cards come from an injected
  `CardSource`, so tests and replays are deterministic.
* `Game.grid` is an immutable snapshot; the board cannot be mutated from outside.
* An invalid move from a selector fails loudly (`InvalidMoveError`). The console
  human re-prompts by itself; the pygame human can only click valid cells.
* A line gives a bonus only if it is **newly** completed, and never on the last turn.
* The pygame package is `ui/pygame_ui` (not `ui/pygame`) so it never shadows the
  real `pygame` library. It is imported lazily: console users don't need pygame.

## 6. Tests

| File | Covers |
|------|--------|
| `tests/test_board.py`, `test_card.py`, `test_game.py` | `core/`: lines, painting, clipping, bonus, shared turns, winner |
| `tests/test_match_runner.py`, `test_application.py` | the glue, with fake renderers/menus/selectors (`tests/helpers.py`) |
| `tests/test_cmd.py` | console UI, a full scripted match, `main.py` wiring and default UI |
| `tests/test_pygame_ui.py` | pygame UI run headless (SDL dummy driver): layout, clicks, menus, a full match; skipped if pygame is missing |

After changing a rule, run `pytest`: `tests/test_game.py` is the place to add a test for it.
