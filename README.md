# Grid Color War

Turn-based strategy game on a grid for **2 to 6 players**, each with its own color (RED, BLUE, GREEN, YELLOW, PURPLE, ORANGE). Every game has its **own settings**: players, board, turns, rules.

* Players play in turn. Each turn a random 3x3 card appears with 4 cells colored in the current player's color.
* You see the **current card and the next two** (their color depends on who will play them).
* The player picks a board cell: the card's **center** goes there and its 4 colored
  cells **overwrite** the board (parts outside the board are ignored).
* The match lasts **50 turns shared by all the players**. The player with the most
  cells wins (a tie is a draw). Then: replay (same settings) or back to the home page.
* Before each game you choose its settings (see "Settings of a game"): number of players, board size, turns, cells per card, and which rules are on.
* Everything else is a **rule** that you can switch on or off (section "Rules"). By default:
  * **line_bonus** - completing a *new* full line (row, column, diagonal) gives an extra move;
  * **full_board_win** - when the **whole grid is covered** (by one player or by several) the game **ends immediately**: if one player owns every cell that player wins; otherwise the player with the most cells wins;
  * **line_streak_wipe** - completing a line on **3 consecutive moves** makes you lose all
    your cells (they become neutral) and the next player plays;
  * **catch_up_cards** - a player more than **10 cells behind** the best other player gets a card
    with a full line (plus the extra cell); a player more than 10 cells ahead of everybody gets a
    card with a neutral center.
  * (off by default: **full_board_flip** - filling the grid gives it to the next player instead.)

## Run

```bash
pip install -r requirements.txt     # pygame (only needed for the window UI)
python main.py                      # pygame window (default)
python main.py --ui cmd             # console version, no dependencies
pip install -r requirements-web.txt # FastAPI + uvicorn, only for the website
python main.py --ui web             # website: open http://127.0.0.1:8000
python main.py --ui web --host 0.0.0.0 --port 8080   # reachable from your network
python main.py --players 4 --board-size 7 --turns 80 # starting values of the settings

pip install -r requirements-dev.txt && pytest     # run the tests
```

**pygame:** Play opens the **settings screen** of the game (see below), then click a cell
(a translucent preview shows where the card will paint). `Esc` quits to the home page;
closing the window exits. Menus: Enter/1 Play, Esc/2 Quit, R Replay, H Home.
**console:** type `row col` (1-5), e.g. `3 4`; `q` quits to the home page. The console has no
settings screen: use the command-line options (`--players`, `--disable`...).

All players share the same screen and take turns (**hot-seat**). Players on different devices
are not implemented: see section 4b for what it would need.
**web:** the home page has the **settings form**; press Play, click a cell (hover shows the
preview), `Esc` goes home. Reloading the page resumes your game.

---

## Settings of a game (each game has its own)

Before each game you choose its configuration; **Replay** reuses it, and the next game starts
from the previous values.

| Setting | Range in the screens | Meaning |
|---------|----------------------|---------|
| Players | 2 - 6 | colors in this order: RED, BLUE, GREEN, YELLOW, PURPLE, ORANGE; this is also the **turn order** |
| Board size | 3 - 9 | the board is size x size |
| Turns (shared by all) | 5 - 500 | total moves of ALL the players together (a bonus move counts) |
| Colored cells per card | 1 - 9 | how many cells of the 3x3 card are colored |
| Cards shown ahead | 0 - 3 | "Coming next" |
| Diagonals count as lines | on / off | for `line_bonus` and `line_streak_wipe` |
| Rules | each on/off + its options | see the next section |

* **pygame:** Play -> *Game settings* screen: `-` / `+` buttons, checkboxes, a button that cycles
  a choice; hover a rule to read what it does; **Start game**, **Defaults**, **Back**
  (Enter = Start, Esc = Back).
* **web:** the home page *is* the form (it is built from `GET /api/settings`); every game is
  created with its own configuration (`POST /api/games`, see section 4b).
* **console / starting values:** `--players N --board-size N --turns N` and the rule switches below.
  In pygame and web they are the values the screen starts from.

---

## Rules: switch them on and off

The game engine only knows the basics (stamp a card, alternate players, shared turns,
most cells wins). Every special behavior is a **rule**: one small file in `core/rules/`,
independent from the others, that you can switch on/off to compare ways of playing.

| Rule (name)        | Default | What it does | File | Options |
|--------------------|---------|--------------|------|---------|
| `full_board_win`   | on  | As soon as **no cell is neutral any more** (the grid is covered by one player or by several) the game **ends immediately**. One player owns everything: that player wins. Otherwise the player with the most cells wins, or - with `winner=mover` - the player whose card filled the last cell. | `core/rules/full_board_win.py` | `winner=most_cells` (or `mover`) |
| `full_board_flip`  | off | A player who colors the whole grid with its color sees every cell go to the **next player** (turn order), who plays. (An alternative to `full_board_win`.) | `core/rules/full_board_flip.py` | - |
| `line_streak_wipe` | on  | Completing a line on `limit` consecutive moves wipes all *your* cells (they become neutral); the next player plays. | `core/rules/line_streak_wipe.py` | `limit=3` |
| `line_bonus`       | on  | Completing a **new** full line gives another move (not on the last turn; never after a penalty). | `core/rules/line_bonus.py` | - |
| `catch_up_cards`   | on  | A player is compared with the **best of the other players**. **More than** `gap` cells behind: its card contains a full line (+ the extra cell, still 4 colored cells). More than `gap` cells ahead of **everybody**: its card has a **neutral center** (still 4 colored cells). | `core/rules/catch_up_cards.py` | `gap=10` |

**Switch rules from the command line** (works with `--ui pygame|cmd|web`):

```bash
python main.py --list-rules                        # all rules, [x] = on, with their options
python main.py --disable catch_up_cards            # turn one off (comma-separated lists work)
python main.py --enable full_board_flip --disable full_board_win
python main.py --only line_bonus                   # ONLY these rules are on
python main.py --only none                         # plain game: no special rule at all
python main.py --set line_streak_wipe.limit=2 --set catch_up_cards.gap=5
python main.py --set full_board_win.winner=mover   # the player who fills the last cell wins
```
(In pygame and web the same switches are checkboxes in the settings screen.)

**Switch rules in code** (tests, experiments): `core/config.py` holds the default, or build a `GameConfig`:

```python
from core import GameConfig, RuleSet
GameConfig(rules=RuleSet.default().without("catch_up_cards"))
GameConfig(rules=RuleSet.of("line_bonus", "full_board_win"))
GameConfig(rules=RuleSet.none())
GameConfig(rules=RuleSet.default().with_("full_board_flip").without("full_board_win")
                          .with_options("line_streak_wipe", limit=2))
```

**Execution order and precedence** (`core/rules/registry.py`, the `RULES` tuple):
`full_board_win` -> `full_board_flip` -> `line_streak_wipe` -> `line_bonus` (`catch_up_cards` works
on cards, not on moves). As soon as a rule *decides* the move (ends the game, or passes the turn
as a penalty) the following ones are skipped. So: if `full_board_win` and `full_board_flip` are
both on, the win happens and the flip never does; a penalized move never gets a bonus turn.

**How a rule works** (`core/rules/base.py`): a `Rule` has two optional hooks:
* `after_move(ctx)` - after the card was stamped. `ctx` gives the board, the player, the next
  player, everybody (`ctx.players`), the changed cells, the new lines, the line streak, the turns
  left; the rule can change the board, grant `ctx.bonus_turn`, call `ctx.pass_turn()` or
  `ctx.end_game(winner)` (no winner given: the player with the most cells wins), and
  `ctx.add_event(code, text)` to say what it did (the text is shown by every UI; `{player}` and
  `{next}` - the player who plays next - are filled in).
* `adjust_card(card, ctx)` - when a card becomes the current one (the player and the scores are known).

**Test a rule alone:** build a `MoveContext` / `CardContext` by hand and call the hook: no `Game`
needed (see `tests/test_rule_units.py`). **Test combinations:** build a `Game` with a `RuleSet`
(see `tests/test_game_rules.py`; one test plays random games under *every* on/off combination).

---

## 1. Project map

```
main.py             composition root: picks the UI and the players (the ONLY file that does)
application.py      home page -> settings of THIS game -> match -> replay/home loop
match_runner.py     plays ONE match: render -> ask move -> play -> repeat

core/               the game itself; imports nothing from the rest of the project
  models.py           Player (name + color), the PALETTE of 6, Position, MoveResult, RuleEvent, Grid
  config.py           GameConfig (players, board, turns, rules...) + to_dict/from_dict + SETTINGS schema
  board.py            Board: cells, painting, "full line" detection
  card.py             Card (+ with_line / with_neutral_center helpers), CardSource, RandomCardSource
  game.py             Game: the ENGINE (stamp, turns, card queue, winner) that calls the rules
  rules/              one file per rule, switchable (see section "Rules")
    base.py             Rule interface, Option (typed settings), MoveContext, CardContext
    registry.py         the list of rules + their execution order
    ruleset.py          RuleSet: which rules are on, their options, (de)serialization
    line_bonus.py full_board_win.py full_board_flip.py line_streak_wipe.py catch_up_cards.py
  errors.py           InvalidMoveError

players/            HOW A MOVE IS CHOSEN
  base.py             MoveSelector (interface), MatchAborted

ui/                 HOW THINGS ARE SHOWN
  base.py             Renderer + Menu (interfaces), MainChoice / AfterMatchChoice
  messages.py         texts shared by every UI ("X played at row...", "X wins!")
  cmd/                console implementation
    ansi.py             colors, block characters, clear screen
    renderer.py         draws the board/scores/card as text
    menu.py             home page + replay question (no settings screen: uses the CLI options)
    human_player.py     reads "row col" from the keyboard
  pygame_ui/          pygame implementation
    window.py           the window, clock, event queue (shared by the 3 classes below)
    theme.py            window size, colors, fonts
    layout.py           where things are (board + sidebar) + pixel -> cell mapping
    drawing.py          drawing functions + Button
    renderer.py         draws a frame
    menu.py             home page + replay buttons
    settings.py         the settings screen of a game (built from the core schema)
    human_player.py     mouse click -> move
  web/                website: FastAPI server + static page (see section 4b)
    app.py              HTTP endpoints (thin layer)
    session.py          GameSession / SessionStore: games kept in memory on the server
    view.py             Game -> JSON dict sent to the browser
    static/index.html   page structure and fixed texts (the settings form is filled by app.js)
    static/style.css    all the look (colors are CSS variables at the top)
    static/app.js       browser logic: draws the state, sends clicks, hover preview

tests/              pytest; one file per area (see section 6)
  e2e_browser/        optional: drives the real website in headless Chrome (section 6)
```

**Dependency rule** (arrows = "may import"):

```
main -> application, match_runner -> ui.base, players.base -> core
ui/cmd, ui/pygame_ui -> ui.base, ui.messages, players.base -> core
ui/web -> ui.messages -> core      (the web UI does not use the blocking interfaces: see 4b)
```
`core` knows nothing about UI or players. The glue files never import `ui/cmd`,
`ui/pygame_ui` or `ui/web`: only `main.py` does.

**One turn, step by step** (`match_runner.py`):
`renderer.render_game(game, last_move)` -> `selector.choose_move(game)` ->
`game.play(position)` -> loop until `game.is_over` -> `render_game_over`.

---

## 2. "I want to change X" -> which file

### Game rules and settings

| I want to change...                         | Edit | Exactly what |
|---------------------------------------------|------|--------------|
| what counts as a "full line" (e.g. only rows, longer lines) | `core/board.py` | `Board._lines()` (it yields every line as a label + list of positions) |
| board size, number of turns, card size, colored cells per card, diagonals on/off, how many upcoming cards are shown, number of players: the **defaults** | `core/config.py` | the default values of `GameConfig` (or the `--players/--board-size/--turns` flags). Players choose their own per game in the settings screens |
| **a new game setting** (a new field shown in the settings screens) | `core/config.py` | add the field to `GameConfig`, to `to_dict()`/`from_dict()` (`_FIELD_KINDS`), and a `Setting(...)` line in `SETTINGS`: both screens show it automatically |
| the colors / names / number of available players | `core/models.py` | the `Player.RED...` constants, `PALETTE`, `MIN_PLAYERS`/`MAX_PLAYERS` (the pygame score row fits up to 6) |
| the turn order, who plays after a bonus turn | `core/game.py` | `Game._advance()`, `Game.next_player` (the order of `GameConfig.players`) |
| **which rules are on/off**, the line-streak limit, the catch-up gap | command line (`--disable`, `--enable`, `--only`, `--set`) or `core/config.py` (`rules=` default) | see section "Rules" |
| when the extra move is granted               | `core/rules/line_bonus.py` | `LineBonus.after_move()` |
| filling the whole grid: who wins / what happens | `core/rules/full_board_win.py` or `full_board_flip.py` | `after_move()` |
| the line-streak penalty (what is lost, who plays next) | `core/rules/line_streak_wipe.py` | `LineStreakWipe.after_move()`; the streak counter itself is updated in `Game.play()` |
| the better card for the trailing player / worse card for the leader, the "more than 10" threshold | `core/rules/catch_up_cards.py` (when) and `core/card.py` (what the cards become) | `CatchUpCards.adjust_card()`, `Card.with_line()`, `Card.with_neutral_center()` |
| which rule runs first / which wins when two apply to the same move | `core/rules/registry.py` | the order of the `RULES` tuple |
| the wording of what a rule did (shown by all UIs) | the rule's own file | the text given to `ctx.add_event(...)` / `Card.with_note(...)` |
| **a brand new rule**                          | new file in `core/rules/` + 1 line in `registry.py` | see section 3, "Add a new rule" |
| how turns pass / who plays next             | `core/game.py` | `Game._advance()` |
| the upcoming-cards queue (how many, when they are drawn) | `core/game.py` | `Game.__init__` (`self._upcoming`), `Game.upcoming_cards`, `Game._draw_base_card()` |
| when a rule may adjust a card (the player and scores are known) | `core/game.py` | `Game._adapt_card()` |
| what is stored about a move (for replays, logs, network) | `core/models.py` | `MoveResult` (incl. `events`, `line_streak`), filled at the end of `Game.play()` |
| what happens at the board edges (card clipped) | `core/game.py` | `Game.painted_cells()` |
| how cards are generated (shape, number of cells, a fixed deck, same cards for both players...) | `core/card.py` | `RandomCardSource.next_card()`, or write a new `CardSource` class and use it in `main.py` (`new_game()`) |
| how the winner is decided / how scores are counted | `core/game.py` | `Game.winner()` (a rule can force it) and `Game.scores()` (cell counting is `Board.count()` in `core/board.py`) |
| when the game ends                          | `core/game.py` | `Game.is_over` (turns ran out, or a rule called `ctx.end_game()`) and `GameConfig.total_turns` |

### Settings screens

| I want to change...                           | Edit | Exactly what |
|-----------------------------------------------|------|--------------|
| what a game parameter is called / its range / its step | `core/config.py` | the `SETTINGS` tuple (`Setting(key, label, kind, minimum, maximum, step)`) |
| what a rule option is called / its range / its choices | the rule's file | its `options_spec` (`Option(default, label, minimum, maximum, choices)`) |
| the look and layout of the pygame settings screen | `ui/pygame_ui/settings.py` | the constants at the top (`LEFT_X`, `RIGHT_X`, `TOP`...) and `SettingsScreen._draw()` |
| how the pygame screen behaves (clicks, keys, errors) | `ui/pygame_ui/settings.py` | `SettingsScreen.run()` |
| the look of the web settings form             | `ui/web/static/style.css` | `.settings`, `.panel`, `.row`, `.rule` |
| how the web form is built / read / sent       | `ui/web/static/app.js` | `buildSettingsForm()`, `applyConfigToForm()`, `collectConfig()`, `startMatch()` |
| what the server accepts for a new game        | `core/config.py` | `GameConfig.from_dict()` (errors become HTTP 400 with the message) |

### Who plays (humans, bots, network, neural network, LLM)

| I want to...                                  | Edit |
|-----------------------------------------------|------|
| make some players bots / network players      | `main.py`: the `selectors = human` line in `build_application()`: replace it with a mapping `{Player.RED: human, Player.BLUE: my_bot, ...}` that covers every player of the game (one `MoveSelector` alone serves all players) |
| write a new kind of player                    | new file in `players/` implementing `MoveSelector.choose_move(game) -> Position` (see section 3) |
| change how a human clicks / types their move  | `ui/pygame_ui/human_player.py` or `ui/cmd/human_player.py` |
| change what a player can see about the game   | nothing to edit: a selector gets the whole `Game` (`current_player`, `grid`, `current_card`, `upcoming_cards`, `players`, `next_player`, `rule_names`, `line_streak`, `line_streak_limit`, `turns_left`, `painted_cells(position)`, `scores()`, `winners()`) |

### pygame look and behavior

| I want to change...                           | Edit | Exactly what |
|-----------------------------------------------|------|--------------|
| window size, all colors, font sizes           | `ui/pygame_ui/theme.py` | `WINDOW_SIZE`, the color constants, `PLAYER_COLORS`, `Fonts.create()` |
| window title, frame rate                      | `ui/pygame_ui/window.py` | the `title` and `fps` parameters of `PygameWindow.__init__` |
| board position/size, gap between cells     | `ui/pygame_ui/layout.py` | class constants `GAP`, `BOARD_LEFT`, `BOARD_TOP`, `BOARD_AREA` |
| the sidebar: current card, the rule note under it, upcoming cards, streak text, rules list (positions, sizes) | `ui/pygame_ui/layout.py` | `SIDEBAR_X`, `CARD_ORIGIN`, `CARD_CELL`, `CARD_GAP`, `CARD_NOTE_POS`, `NEXT_ORIGIN`, `NEXT_CELL`, `NEXT_GAP`, `NEXT_SPACING`, `STREAK_POS`, `RULES_POS` |
| how the current / upcoming cards are drawn (colors, neutral gray of upcoming cards) | `ui/pygame_ui/drawing.py` | `_draw_current_card()`, `_draw_upcoming_cards()`, `_draw_card()`; the gray is `NEUTRAL_CARD` in `theme.py` |
| the line-streak counter and its warning     | `ui/pygame_ui/drawing.py` | `_draw_streak()` (`WARNING` color in `theme.py`) |
| rounded corners, how cells/board/card are drawn | `ui/pygame_ui/drawing.py` | `CELL_RADIUS`, `_draw_board()`, `_draw_card()` |
| the score boxes, "Turns left", the title      | `ui/pygame_ui/drawing.py` | `_draw_scores()` and `draw_scene()` |
| the hover preview (color, opacity, outline)   | `ui/pygame_ui/drawing.py` | `draw_preview()` |
| the GAME OVER overlay                         | `ui/pygame_ui/drawing.py` | `draw_game_over()` |
| the hint text at the bottom, the message under the board | `ui/pygame_ui/drawing.py` | end of `draw_scene()`, `_draw_message()` (wrapped to the board's width) |
| home page: title, buttons, labels, positions, keyboard shortcuts | `ui/pygame_ui/menu.py` | `main_menu_buttons()`, `after_match_buttons()` (shown in the sidebar at game over), `ask_main_choice()`, the `keys` dictionaries |
| button look (colors, border)                  | `ui/pygame_ui/drawing.py` (`Button.draw`) and `theme.py` (`BUTTON`, `BUTTON_HOVER`) |
| mouse/keyboard behavior during a match (e.g. right click, Esc) | `ui/pygame_ui/human_player.py` | `PygameHumanPlayer.choose_move()` |

Limits to know: the sidebar is sized for **3x3** cards; a bigger `card_size` needs a
bigger `WINDOW_SIZE` and new `Layout` positions (`CARD_ORIGIN`, `NEXT_ORIGIN`...).
Any board size works: cell size is computed from `Layout.BOARD_AREA`.

### Website look and behavior

| I want to change...                           | Edit | Exactly what |
|-----------------------------------------------|------|--------------|
| colors, spacing, corner radius, fonts         | `ui/web/static/style.css` | the variables in `:root` at the top (`--red`, `--blue`, `--bg`, `--cell-radius`...) |
| board / card / sidebar sizes, phone layout    | `ui/web/static/style.css` | `.board-col`, `.sidebar`, `.card.big`, `.card.small`, `.layout` (it wraps on narrow screens) |
| the home page text, titles, buttons, hint     | `ui/web/static/index.html` | the `#home` and `#match` sections |
| click / hover / Esc behavior, reload-resume   | `ui/web/static/app.js` | `playCell()`, `goHome()`, `startMatch()`, `updatePreview()`, the event handlers at the bottom, `init()` |
| how the board, cards, score, streak, game over are drawn | `ui/web/static/app.js` | `renderBoard()`, `renderCards()`, `renderScores()`, `renderGameOver()`, `cardElement()` |
| what data the browser receives (add a field)  | `ui/web/view.py` | `game_to_dict()` / `move_to_dict()`; then use it in `app.js` |
| the endpoints, status codes, error messages   | `ui/web/app.py` | `create_app()` |
| how many games are kept in memory             | `ui/web/session.py` and the `max_sessions` argument of `create_app()` | `SessionStore` |
| host and port                                 | command line | `--host`, `--port` (defaults in `main()` in `main.py`) |
| rules for the website (turns, board size...)  | `main.py` | pass `config=GameConfig(...)` to `run_web(...)` in `main()` |

### Console look and behavior

| I want to change...                           | Edit | Exactly what |
|-----------------------------------------------|------|--------------|
| colors, block characters, clear screen        | `ui/cmd/ansi.py` | `_FG`, `_BG`, `_BG_EMPTY`, `cell_block()`, and `neutral_block()` / `_BG_NEUTRAL` for the upcoming cards |
| what is printed each turn (header, scores, board, cards) | `ui/cmd/renderer.py` | `CmdRenderer.render_game()`, `_board_text()`, `_cards_text()` (current + upcoming cards side by side), `_card_rows()` |
| the game over screen                          | `ui/cmd/renderer.py` | `CmdRenderer.render_game_over()` |
| the accepted input format / quit words        | `ui/cmd/human_player.py` | `parse_position()`, `QUIT_WORDS`, the prompt in `choose_move()` |
| home page and replay question                 | `ui/cmd/menu.py` | `ask_main_choice()`, `ask_after_match()` |

### Texts and flow

| I want to change...                           | Edit | Exactly what |
|-----------------------------------------------|------|--------------|
| the wording of "X played at row...", "plays again", the two penalties, "wins" (shared by console, pygame **and** website) | `ui/messages.py` | `describe_start()`, `describe_move()`, `describe_outcome()` |
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
Then in `main.py` (`build_application`), a mapping that covers **every player of the game** (a game
has up to 6 players; `Player.GREEN`, `Player.YELLOW`... exist too):

```python
from players.random_bot import RandomBot
selectors = {Player.RED: human, Player.BLUE: RandomBot()}   # for a 2-player game
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

> The website is the exception: the browser owns the loop, so it does not implement
> these three interfaces. See section 4b.

### Add a new rule

1. Create `core/rules/my_rule.py`:

```python
from core.models import Position
from core.rules.base import MoveContext, Option, Rule

class CornerBonus(Rule):
    name = "my_rule"                        # used by --enable/--disable and RuleSet
    description = "Painting all 4 corners gives another move."
    enabled_by_default = False              # off until you switch it on
    options_spec = {"corners": Option(4, "Corners needed", minimum=1, maximum=4)}  # optional

    def after_move(self, ctx: MoveContext) -> None:
        n = ctx.board.size - 1
        corners = [(0, 0), (0, n), (n, 0), (n, n)]
        if sum(ctx.board.get(Position(*c)) is ctx.player for c in corners) >= self.option("corners"):
            ctx.bonus_turn = True
            ctx.add_event("corner_bonus", "{player} owns the corners and plays again!")
```
   To change cards instead, override `adjust_card(card, ctx)`.
2. Add it to the `RULES` tuple in `core/rules/registry.py` (the position in the tuple is its execution order).
3. Done: `python main.py --list-rules` shows it, `--enable my_rule` turns it on, the settings screens
   (pygame and web) list it with its option, and every UI displays its event text. Test it alone like the ones in `tests/test_rule_units.py`.

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

## 4b. How the website fits (server owns the game, browser owns the loop)

The console and pygame UIs are *blocking*: our program runs the loop and calls
`renderer.render_game()` / `selector.choose_move()`. On the web the **browser** runs
the loop (a click arrives whenever the user clicks), so the three blocking
interfaces are replaced by a small HTTP API over a `GameSession`:

```
browser (index.html + app.js)  --HTTP/JSON-->  FastAPI (ui/web/app.py)
        draws the state                          GameSession -> core.Game (the same rules)
        sends clicks                             view.py -> JSON, texts from ui/messages.py
```
All rules stay on the server; the browser only draws and sends clicks. The one thing
the browser computes is the hover preview (which cells the card would paint).

| Endpoint | Does |
|----------|------|
| `GET /api/settings` | the settings schema: parameters, rules (with descriptions and option specs) and defaults: the browser builds its form from it |
| `POST /api/games` body `{"config": {...}}` (optional) | new game with **its own configuration** -> full state (201); `config` is any subset of `GameConfig.to_dict()` (`num_players`, `board_size`, `total_turns`, `rules: {enabled, options}`...), the rest is the server default; 400 with a readable message if invalid |
| `GET /api/games/{id}` | current state (used to resume after a reload) |
| `POST /api/games/{id}/moves` body `{"row": 2, "col": 3}` (0-indexed) | play the current card there -> new state; 400 if invalid |
| `DELETE /api/games/{id}` | forget the game (Home / Replay) |
| `GET /` , `/static/*` | the page |
| `GET /docs` | interactive API docs generated by FastAPI |

State = `players` (name + color, in turn order), `grid`, `current_player`, `scores`, `turns_left`,
`current_card`, `upcoming_cards`, `line_streak`, `last_move` (with its rule `events`), `message`
(lines of text), `is_over`, `winner`, `winners`, `outcome`, `rules`, `config` (what the form needs
for Replay): see `ui/web/view.py`.

Today the website is **hot-seat** (all the players share the browser), like the other
UIs. Natural next steps, both small because `core` is untouched:
* **Players on different devices:** give each game one seat token per player (created in
  `SessionStore.create`), make `GameSession.play` check that the token matches
  `current_player`, and poll `GET` (or add a WebSocket) so the waiting browsers see
  the other players' moves.
* **Bots:** give `GameSession` a `{Player: MoveSelector}` mapping; after a human move,
  while the current player has a selector, call `selector.choose_move(game)` and
  `game.play(...)`. Any `MoveSelector` (neural network, LLM...) plugs in unchanged.

Deployment notes: sessions live in memory, so run **one** process (no `--workers`);
restarting the server forgets running games; there is no login. Fine for a LAN or a
small demo. For the public internet, put it behind a reverse proxy and add
authentication and rate limiting first.

## 5. Design decisions

* `Game` has no randomness or I/O of its own: cards come from an injected
  `CardSource`, so tests and replays are deterministic.
* `Game.grid` is an immutable snapshot; the board cannot be mutated from outside.
* An invalid move from a selector fails loudly (`InvalidMoveError`). The console
  human re-prompts by itself; the pygame human can only click valid cells.
* The engine (`Game`) only does the basics; **all special behavior lives in rules** that the
  engine calls in a fixed order (`registry.py`). A rule that *decides* the move stops the
  following ones, so precedence is simply the order of the list.
* A line gives a bonus only if it is **newly** completed, and never on the last turn.
* **Players are values** (`Player(name, color)`), compared by value, not identity; the turn order
  is the order of `GameConfig.players`; a bonus turn keeps the same player, any other move passes
  the turn to the next one (wrapping around). Turns are shared by all the players, so with more
  players each one plays fewer moves: raise `total_turns` in the settings.
* **Ranking**: the player with the most cells wins; if several are tied at the top, `winners()`
  lists them and `winner()` is None (the UIs say "X and Y tie for the win!", or "It's a draw!"
  when everybody is tied).
* **Full grid** (`full_board_win`) = no neutral cell left, whoever owns the cells. The game ends
  at once and `turns_left` stays as it was. One player owns everything: that player wins. A grid
  covered by several players: the player with the most cells wins (`winner=most_cells`, the
  default) or the player whose card filled the last cell (`winner=mover`). **`full_board_flip`**
  needs a move that changes at least one cell and leaves every cell in the mover's color (that
  stops it from flipping back and forth); the board goes to the next player in turn order.
* **Per-game settings**: a `GameConfig` is created for each game and never changed (immutable).
  The settings screens are generated from `SETTINGS` and the rules' `options_spec`, so there is a
  single place to define a parameter, its range and its label. Every value is validated by the
  core (`GameConfig.from_dict`), whatever UI sent it.
* **Line streak** = consecutive moves of the same player that each completed a new line (that
  is exactly a chain of bonus moves). After the wipe, the turn goes to the next player and the
  streak restarts at 0. Only the wiping player's cells are removed. The streak is tracked by the
  engine (a fact), the rule only reads it, so it stays correct even if another rule decided the move.
* **Catch-up cards**: with several players each one is compared with the **best of the other
  players**: more than `gap` behind it gets the line card, more than `gap` ahead of every other
  player it gets the neutral-center card (with 2 players this is the plain difference).
  "More than 10" means a difference of 11 or more (exactly 10 changes nothing).
  The adjustment is made at the moment a card *becomes the current card*, using the scores after
  the previous move and the player who will really play it (so it is right after a bonus turn too).
  The upcoming cards in "Coming next" are shown as drawn, before any adjustment, because who
  will play them and with what scores is not known yet.
  The adjusted card is derived from the drawn card, with no extra randomness: the trailing
  player's card becomes the line that already fits it best (3 cells) plus one of its other cells
  (4 colored cells in total); the leader's card moves a colored center to the nearest free cell
  (still 4 colored cells; a card whose center is already neutral stays as it is).
* Upcoming cards are shown as shapes in neutral color: who will play them is not known yet (a
  bonus or a penalty changes the order). Near the end of the match only the cards that will
  really be played are shown.
* The pygame package is `ui/pygame_ui` (not `ui/pygame`) so it never shadows the
  real `pygame` library. It is imported lazily: console users don't need pygame.

## 6. Tests

| File | Covers |
|------|--------|
| `tests/test_board.py`, `test_card.py`, `test_game.py` | `core/` basics: lines, painting, clipping, card helpers (`with_line`, `with_neutral_center`), shared turns, winner |
| `tests/test_rule_units.py`                    | **each rule tested alone** with a hand-made context (no `Game`) |
| `tests/test_ruleset.py`                       | the on/off switches: defaults, `with_`/`without`/`of`/`none`, options, validation, order, (de)serialization |
| `tests/test_config.py`                        | `GameConfig`: players, validation, `to_dict`/`from_dict` with readable errors, and that every value a settings screen can offer is accepted by the core |
| `tests/test_game_rules.py`                    | rules inside a `Game`: each alone, combinations, precedence, catch-up cards, upcoming cards, a custom rule, **several players** (turn order, ties, bonus turns, grid covered by several), and random games under **every** on/off combination |
| `tests/test_messages.py`                      | the shared texts built from rule events |
| `tests/test_match_runner.py`, `test_application.py` | the glue, with fake renderers/menus/selectors (`tests/helpers.py`) |
| `tests/test_cmd.py` | console UI, a full scripted match, `main.py` wiring, the `--enable/--disable/--only/--set/--list-rules` switches |
| `tests/test_web.py` | the HTTP API (FastAPI TestClient): create / play / invalid / 404 / full match, **per-game config and its errors**, 3 players, the settings schema, rules, eviction, static files, `main.py --ui web`; skipped if fastapi or httpx is missing |
| `tests/test_pygame_ui.py` | pygame UI run headless (SDL dummy driver): layout, clicks, menus, **the settings screen** (steppers, checkboxes, rule options, Defaults, Back, limits), a full 3-player flow home -> settings -> match -> home; skipped if pygame is missing |

**Browser end-to-end test (optional, needs Node.js):** `tests/e2e_browser/e2e.mjs` opens
the real website in headless Chrome and checks about 40 things (play, hover preview, rules list, the **settings form**,
a **3-player game** with its turn rotation, Replay keeping the settings, Defaults, a refused
configuration explained on the page, reload-resume, Esc, a full 50-turn match, phone width, no
unexpected console errors)
and saves screenshots. Run it after editing `ui/web/static/*`:

```bash
python main.py --ui web --port 8123                    # terminal 1
cd tests/e2e_browser && npm install && node e2e.mjs    # terminal 2 (Linux: bundled Chromium)
CHROME_PATH="/path/to/chrome" node e2e.mjs             # Windows/macOS: your own Chrome
```

After changing a rule, run `pytest`: `tests/test_rule_units.py` (the rule alone) and `tests/test_game_rules.py` (in a game) are the places to add a test for it.
