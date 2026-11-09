# Grid Color War: specification

| | |
|---|---|
| **Document** | Functional and technical specification, *current state* |
| **Version** | 0.1 (describes the code as delivered on 2026-11-09) |
| **Product** | Turn-based card-stamping strategy game for 2 to 6 players |
| **Interfaces** | pygame window (default), website (FastAPI + browser), console |
| **Language** | Python 3.9+ (core, servers, pygame, console), JavaScript (browser client) |

How to read this document:

* Requirements have an ID (`GM-3`, `RL-12`...) so they can be referenced in tickets and tests.
  "**shall**" = implemented behavior that tests protect; "**may**" = optional behavior.
* **Status** is one of: ✅ implemented and tested, 🟡 implemented with a limitation (see section 12),
  ⛔ not implemented (see section 12 and 13).
* Section 13 lists the places where the original request left room for interpretation, and what was chosen.

---

## 1. Purpose and scope

Players take turns stamping a small colored **card** onto a **grid**. Each stamp overwrites
the colors under it. The player who owns the most cells when the game ends wins. A set of
independent, switchable **rules** adds bonuses, penalties, catch-up mechanics and an early
ending. Every game has its **own configuration** (players, board, turns, rules).

### 1.1 In scope (implemented)

| Area | Status |
|------|--------|
| Game engine for 2 to 6 players on one screen ("hot-seat") | ✅ |
| Five switchable rules, each in its own file, each testable alone | ✅ |
| Per-game configuration, validated, serializable to JSON | ✅ |
| pygame interface with a settings screen | ✅ |
| Website: FastAPI server + HTML/CSS/JS client with a settings form | ✅ |
| Console interface (configured through command-line options) | 🟡 |
| Command-line switches for players, board, turns and rules | ✅ |
| Automated tests: 195 Python tests + 37-check real-browser test | ✅ |

### 1.2 Out of scope (not implemented)

Players on different devices, bots / AI opponents (only the interface exists), accounts and
authentication, persistence of games, spectators, replays or game history, sound, custom player
names or colors, card shapes other than 3x3 in the pygame and web screens.

---

## 2. Glossary

| Term | Meaning |
|------|---------|
| **Grid / board** | Square grid of `board_size` x `board_size` cells. A cell is *neutral* (no owner) or owned by one player. |
| **Player** | A name and an RGB color. Up to 6 exist (the **palette**). Compared by value. |
| **Card** | A 3x3 pattern in which some cells are colored (4 by default). Always shown with the current player's color. |
| **Stamp / move / turn** | Placing the center of the current card on a board cell. One move consumes one shared turn. |
| **Bonus turn** | The same player plays again (does not skip the turn counter). |
| **Line** | A full row, column or (if enabled) diagonal of the board owned by one player. |
| **New line** | A line that did not exist for that player before the move. |
| **Line streak** | Number of consecutive moves of the same player that each completed a new line. |
| **Rule** | A small independent object that can react to a move or adjust a card. Switchable per game. |
| **Event** | A message produced by a rule during a move, with its own wording. |
| **Base card** | A card as drawn from the deck, before any rule adjusted it. |

---

## 3. Basic game mechanics

These always apply. Everything in section 4 is optional.

| ID | Requirement |
|----|-------------|
| **GM-1** | A game has between **2 and 6** players. Their order in the configuration is the **turn order**; the first player starts. |
| **GM-2** | Players are colored in palette order: RED `#e24848`, BLUE `#4285e6`, GREEN `#48b464`, YELLOW `#e6c43c`, PURPLE `#a064dc`, ORANGE `#f08c32`. A game with *N* players uses the first *N*. |
| **GM-3** | The board starts with all cells neutral. |
| **GM-4** | Each turn, one **current card** is dealt. It is a 3x3 pattern with `colored_cells` (default 4) distinct colored cells, chosen at random. |
| **GM-5** | The current player picks a board cell. The **center of the card** is placed on it and every colored card cell **overwrites** the owner of the board cell beneath it. Colors can be overwritten repeatedly. |
| **GM-6** | Card cells that fall outside the board are ignored (clipped). Any board cell may be chosen, including edges and corners. |
| **GM-7** | A move outside the board, or any move after the game is over, is refused with an error and changes nothing. |
| **GM-8** | After a move the turn passes to the next player in turn order, wrapping around, unless a rule grants a bonus turn. |
| **GM-9** | The number of turns, `total_turns` (default 50), is **shared by all players**. Every move, including bonus moves, consumes one. The game is over when none is left. |
| **GM-10** | The game can also be ended early by a rule (section 4). |
| **GM-11** | **Ranking**: the player with the most cells wins. If several players tie for the most cells, they are all reported as winners and there is no single winner (draw). |
| **GM-12** | The next **2 cards** (`preview_cards`, 0 to 3) are visible in advance. Only cards that will actually be played are shown: near the end there are fewer, and none after the game is over. |
| **GM-13** | The engine tracks the **line streak** (consecutive line-completing moves of the current player). It resets when a move completes no new line and whenever the turn passes to another player. |
| **GM-14** | Lines are rows and columns, plus both diagonals when `diagonals_count` is on (default on). Line labels are `row n`, `column n`, `diagonal \` and `diagonal /`. |
| **GM-15** | Cards come from an injectable source, so games can be made fully deterministic (tests, replays). The default source is random. |

Status: ✅ (tests: `test_board.py`, `test_card.py`, `test_game.py`, `test_game_rules.py`).

---

## 4. Special rules

### 4.1 Overview

| Rule (name) | Default | One-line behavior | Options (range) |
|-------------|---------|-------------------|-----------------|
| `full_board_win` | **on** | The game ends the moment no cell is neutral. | `winner`: `most_cells` (default) or `mover` |
| `full_board_flip` | off | Filling the whole grid with your color gives every cell to the next player. | none |
| `line_streak_wipe` | **on** | Completing lines on *N* consecutive moves wipes your cells. | `limit` 1-20 (default 3) |
| `line_bonus` | **on** | Completing a new line gives another move. | none |
| `catch_up_cards` | **on** | Trailing players get a better card, a dominating player a worse one. | `gap` 0-100 (default 10) |

### 4.2 Rule mechanism

| ID | Requirement |
|----|-------------|
| **RL-1** | Each rule is a class with a unique `name`, a `description`, a default on/off state and optional typed **options** (default, label, integer range or list of choices). |
| **RL-2** | A rule has two optional hooks: `after_move(ctx)`, called after a card is stamped, and `adjust_card(card, ctx)`, called when a card becomes the current card. |
| **RL-3** | In `after_move` a rule may: change the board, grant a bonus turn, **pass the turn** (penalty), **end the game** (with or without a forced winner), and add **events** (code + text). |
| **RL-4** | `after_move` hooks run in a fixed **execution order**: `full_board_win`, `full_board_flip`, `line_streak_wipe`, `line_bonus`. As soon as a rule *decides* the move (passes the turn or ends the game), the remaining `after_move` hooks are skipped. |
| **RL-5** | Consequences of RL-4: if `full_board_win` and `full_board_flip` are both on, the win happens and the flip never does; a penalized move never receives a bonus turn. |
| **RL-6** | `adjust_card` receives the player who will play the card and the current scores of **all** players. It runs when a card becomes current, so the player and the scores are the real ones, including after a bonus turn. |
| **RL-7** | Rule texts use the placeholders `{player}` (the mover) and `{next}` (the player who plays next); each interface fills them in. |
| **RL-8** | Rule option values are validated when a `RuleSet` is created (unknown option, wrong type, out of range, value not among the choices) and the error message is readable. |
| **RL-9** | A rule set is a value object: it can be built (`default()`, `none()`, `of(...)`), modified (`with_`, `without`, `with_options`), compared by **effective behavior**, and converted to and from a dictionary. |
| **RL-10** | A rule is testable **alone**, without a `Game`, by calling its hook with a hand-made context. |
| **RL-11** | Adding a rule needs one new file and one line in the registry; the command line and both settings screens pick it up automatically. |

### 4.3 `full_board_win`: the grid is covered, the game ends

| ID | Requirement |
|----|-------------|
| **RL-20** | Trigger: after a move, **no board cell is neutral** (the grid is covered by one player or by several). The game ends immediately; the remaining turns are not played. |
| **RL-21** | If one player owns **every** cell, that player wins (event: "`{player}` filled the whole grid and wins immediately!"). |
| **RL-22** | If several players cover the grid and `winner=most_cells`: the player(s) with the most cells win, per GM-11 (event: "The grid is full: the game ends now!"). |
| **RL-23** | If several players cover the grid and `winner=mover`: the player whose card filled the **last** neutral cell wins, even when behind (event: "The grid is full: `{player}` filled the last cell and wins!"). |

### 4.4 `full_board_flip` (off by default)

| ID | Requirement |
|----|-------------|
| **RL-30** | Trigger: a move that **changes at least one cell** and leaves **every** cell in the mover's color. |
| **RL-31** | Effect: every cell becomes the color of the **next player in turn order**; the turn passes to that player; no bonus. The game does not end. |
| **RL-32** | A move that changes nothing on an already single-colored board does not trigger it (prevents flipping back and forth). It also applies on the last turn. |

### 4.5 `line_streak_wipe`

| ID | Requirement |
|----|-------------|
| **RL-40** | Trigger: the player's line streak reaches `limit` (default 3), i.e. `limit` consecutive moves each completed a new line. |
| **RL-41** | Effect: **all cells of that player** become neutral (other players' cells are untouched); the turn passes to the next player; no bonus; the streak restarts at 0. |
| **RL-42** | The streak is a fact tracked by the engine, so it stays correct even if another rule decided an earlier move. |

### 4.6 `line_bonus`

| ID | Requirement |
|----|-------------|
| **RL-50** | Trigger: the move completes at least one **new** line. A line that already existed does not count again. |
| **RL-51** | Effect: the same player plays again. Event: "Full line completed: ...! `{player}` plays again!" |
| **RL-52** | No bonus is given on the very last turn, and none after a penalty or an early end (RL-4). |

### 4.7 `catch_up_cards`

| ID | Requirement |
|----|-------------|
| **RL-60** | For the player who will play a card: *lead* = own score minus the **best score among the other players**. With 2 players this is the plain difference. |
| **RL-61** | If *lead* < -`gap` (more than `gap` cells behind; default 10): the card is replaced by one that contains a **full line** plus the extra cell(s), keeping the same number of colored cells (4). Note: "Catch-up boost: this card contains a full line!" |
| **RL-62** | If *lead* > `gap` (more than `gap` cells ahead of **everybody**): the card gets a **neutral center**: a colored center cell moves to the nearest free card cell, still 4 colored cells. Note: "Leader handicap: the center of this card is neutral." |
| **RL-63** | "More than `gap`" is strict: a difference of exactly `gap` changes nothing. |
| **RL-64** | The adjusted card is **derived from the drawn card** with no extra randomness. Boost: the card line sharing the most cells with the base card (first in row, column, diagonal order on ties) plus the base card's remaining cells as needed. Handicap: nearest free cell by Manhattan distance, then reading order. A card that already satisfies the condition is kept as is (the note is still shown). |
| **RL-65** | Cards shown in "Coming next" are the **base cards**; they are adjusted only when they become current. |
| **RL-66** | A card with fewer colored cells than a line is long cannot be boosted and is left unchanged. |

### 4.8 Event texts and codes

| Code | Produced by | Text |
|------|-------------|------|
| `line_bonus` | `line_bonus` | Full line completed: `<lines>`! / `{player}` plays again! |
| `cells_wiped` | `line_streak_wipe` | Too many lines in a row: `{player}` loses all cells! |
| `board_filled_win` | `full_board_win` | one of the three texts of RL-21 to RL-23 |
| `board_flipped` | `full_board_flip` | The whole board is `{player}`! Every cell switches to `{next}`, and `{next}` plays. |

Move line, shown before the events: "`X` played at row *r*, col *c* (*n* cell(s) changed)."
Outcome texts: "`X` wins!", "It's a draw!" (everybody tied), "`X` and `Y` tie for the win!".
Start text: "Game start! `X` begins."

Status of section 4: ✅ (tests: `test_rule_units.py` alone, `test_ruleset.py`, `test_game_rules.py`
in a game, including random games under **all 32 on/off combinations**).

---

## 5. Configuration

### 5.1 Game parameters

| Key | Type | Default | Screens offer | Core accepts | Meaning |
|-----|------|---------|---------------|--------------|---------|
| `num_players` | int | 2 | 2 to 6 | 2 to 6 | Number of players (palette order = turn order) |
| `board_size` | int | 5 | 3 to 9 | ≥ 1 | Board is size x size |
| `total_turns` | int | 50 | 5 to 500, step 5 | ≥ 1 | Turns shared by all players |
| `colored_cells` | int | 4 | 1 to 9 | 1 to `card_size`² | Colored cells per card |
| `preview_cards` | int | 2 | 0 to 3 | ≥ 0 | Cards shown ahead |
| `diagonals_count` | bool | true | on / off | | Diagonals are lines |
| `card_size` | int | 3 | not offered | odd, ≥ 1 | Card side (the interfaces are laid out for 3) |
| `rules` | object | see 4.1 | per rule | | Which rules are on and their options |

| ID | Requirement |
|----|-------------|
| **CF-1** | A `GameConfig` is **immutable** and belongs to one game. Each new game gets its own. |
| **CF-2** | A configuration converts to and from a JSON-friendly dictionary. Missing keys keep the value of a base configuration (the default one). `num_players` selects the first *N* palette colors. `rules` replaces the whole rule set. |
| **CF-3** | Validation rejects, with a readable message: unknown keys, wrong types (a boolean where a number is expected, a text for a number, a number for a flag), out-of-range values, unknown rule names, invalid rule options. |
| **CF-4** | The settings offered by the screens (`SETTINGS`) are a subset of what the core accepts; a test guarantees every offered value is accepted. |
| **CF-5** | Settings screens are **generated** from the settings list and from each rule's option specs: a new parameter, rule or option appears without UI changes. |
| **CF-6** | Replay reuses the settings of the game just played; the next new game starts from the previous values. |

Example configuration (also the body accepted by the web API under `"config"`):

```json
{
  "num_players": 3, "board_size": 5, "card_size": 3, "colored_cells": 4,
  "total_turns": 60, "diagonals_count": true, "preview_cards": 2,
  "rules": {
    "enabled": ["full_board_win", "line_streak_wipe", "line_bonus", "catch_up_cards"],
    "options": {
      "full_board_win": {"winner": "most_cells"},
      "line_streak_wipe": {"limit": 3},
      "catch_up_cards": {"gap": 10}
    }
  }
}
```

Status: ✅ (tests: `test_config.py`, `test_ruleset.py`, `test_web.py`, `test_pygame_ui.py`).

---

## 6. Architecture

### 6.1 Layers and dependency rule

```
main.py (composition root)
  ├─ application.py   home → settings → match → replay/home loop
  ├─ match_runner.py  plays ONE match
  ├─ ui/              how things are shown (base interfaces + cmd, pygame_ui, web)
  ├─ players/         how a move is chosen (interface)
  └─ core/            the game itself: models, board, card, config, game, rules/
```

* `core` imports nothing from the rest of the project.
* `ui/cmd`, `ui/pygame_ui` depend on `ui.base`, `ui.messages`, `players.base`, `core`.
* `ui/web` depends on `ui.messages` and `core` only (it does not use the blocking interfaces).
* The glue files never import a concrete interface; **only `main.py` does** (pygame and web are imported lazily, so they are optional).

### 6.2 Core components

| Component | Responsibility |
|-----------|----------------|
| `core/models.py` | `Player` (name + color, hashable), `PALETTE`, `Position`, `MoveResult`, `RuleEvent`, `Grid` |
| `core/board.py` | Cells, painting, full-line detection, `is_full`, `is_filled_with`, `fill`, `clear_player`, immutable snapshot |
| `core/card.py` | `Card` and its pure helpers (`lines`, `has_line`, `with_line`, `with_neutral_center`, `with_note`); `CardSource` interface; `RandomCardSource` |
| `core/config.py` | `GameConfig`, `to_dict` / `from_dict`, the `SETTINGS` schema |
| `core/game.py` | The **engine**: stamping, turn order, shared turns, card queue, winners, running the rules; `new_game(config)` |
| `core/rules/` | `base.py` (Rule, Option, MoveContext, CardContext), one file per rule, `registry.py` (list and execution order), `ruleset.py` (RuleSet) |
| `core/errors.py` | `InvalidMoveError` |

| ID | Requirement |
|----|-------------|
| **AR-1** | The engine has no input/output and no randomness of its own; it only knows the basic mechanics of section 3 and calls the rules. |
| **AR-2** | `Game` exposes a read-only state (grid snapshot, players, current and next player, current card, upcoming cards, scores, winners, turns, streak, rule names) and exactly one mutating method, `play(position)`, which returns a `MoveResult` (changed cells, new lines, bonus flag, next player, events, streak). |
| **AR-3** | Players are compared **by value**, never by identity. |
| **AR-4** | The board cannot be mutated from outside the engine: `Game.grid` is an immutable snapshot. |

### 6.3 Interfaces between components

| Interface | Methods | Implemented by |
|-----------|---------|----------------|
| `Rule` | `after_move(ctx)`, `adjust_card(card, ctx)` | the five rules |
| `CardSource` | `next_card()` | `RandomCardSource` (tests use fixed sources) |
| `MoveSelector` (`players/base.py`) | `choose_move(game) → Position`; may raise `MatchAborted` | `CmdHumanPlayer`, `PygameHumanPlayer` |
| `Renderer` (`ui/base.py`) | `render_game(game, last_move)`, `render_game_over(game)` | `CmdRenderer`, `PygameRenderer` |
| `Menu` (`ui/base.py`) | `ask_main_choice()`, `ask_game_config(current)`, `ask_after_match()`, `show_goodbye()` | `CmdMenu`, `PygameMenu` |
| Game factory | `(GameConfig) → Game` | `core.new_game` |

| ID | Requirement |
|----|-------------|
| **AR-5** | A `MoveSelector` receives the whole `Game` as context and returns a decision (a human, a socket, a neural network, an LLM...). It must treat the game as read-only; only `MatchRunner` calls `play`. |
| **AR-6** | `MatchRunner` accepts **one** selector used by every player (hot-seat) or a mapping `{Player: MoveSelector}`; a mapping must cover every player of the game or the match is refused with the names of the missing players. |
| **AR-7** | A selector that returns an invalid move makes `Game.play` raise `InvalidMoveError` (fail loudly). The console human re-prompts by itself; the pygame human can only click valid cells. |

### 6.4 Flow

One turn (`MatchRunner`): `render_game(game, last_move)` → `selector.choose_move(game)` →
`game.play(position)` → repeat until `game.is_over` → final `render_game` → `render_game_over`.
A selector raising `MatchAborted` ends the match without a game-over screen.

Application (`Application`): home → **Play** → `menu.ask_game_config(current)` (`None` = back to home)
→ match → **Replay** (same settings, no new question) or **Home**; aborting a match returns home.

Inside `Game.play`: (1) stamp; (2) compute new lines and update the streak; (3) run `after_move`
hooks in order until one decides; (4) apply an early end if requested; (5) build the result;
(6) advance the turn (bonus or next player) and draw the next card, adjusted by the rules for the
player and scores that now apply.

Status: ✅.

---

## 7. User interfaces

Common behavior (all interfaces): the same texts (`ui/messages.py`), players shown in turn order with
their colors, the active player highlighted, scores, turns left, the current card with its rule note,
"Coming next" cards in a neutral color (their owner is unknown), the line-streak counter with a warning
when one more line would trigger the wipe, the active rules list, and a game-over screen with the scores
and the outcome.

### 7.1 pygame (default interface)  ✅

Window 860 x 700. Requires `pygame`.

| Screen | Behavior |
|--------|----------|
| **Home** | Buttons Play and Quit. Keys: Enter or 1 = Play, Esc or 2 = Quit. |
| **Game settings** | Left: the six parameters with `-` / `+` buttons (and a checkbox for diagonals). Right: the rules with a checkbox each and their options (stepper, or a button cycling the choices); options of a disabled rule are greyed out and inert. Hovering a rule shows its description. Buttons: **Back** (Esc), **Defaults**, **Start game** (Enter). Values are clamped to their ranges; an error from the core is shown in the screen. |
| **Match** | Board on the left (cell size computed from the board size), one score box per player above it (up to 6) with the active one in a thick border, "Turns left" above. Sidebar: current card and its note, "Coming next", line streak, active rules. Under the board: what just happened (wrapped). |
| **Game over** | Translucent overlay on the board with every player's score and the outcome; sidebar buttons Replay (R) and Home (H or Esc). |

Controls during a match: click a cell to play; moving the mouse shows a **translucent preview** of the
cells the card would paint (clipped at the edges); Esc quits to home; clicks outside the board are ignored;
closing the window ends the application.

### 7.2 Website  ✅

Server: FastAPI (`python main.py --ui web`). Client: static HTML, CSS and vanilla JavaScript, no framework
and no external resource.

| Part | Behavior |
|------|----------|
| **Home** | The **settings form**, built from `GET /api/settings`: the six parameters as inputs, each rule with a checkbox, its description and its options. Buttons: Play, Defaults. A server-side refusal is shown under the form. |
| **Match** | Same information as pygame; cells are real buttons (keyboard accessible); hover preview; Esc goes home (the game is deleted on the server). |
| **Game over** | Overlay and buttons Replay (same settings) and Home. |
| **Persistence in the browser** | The id of the running game is kept in `sessionStorage`: reloading the page resumes the game (and refills the form from its configuration). |
| **Responsive** | Sidebar wraps below the board on narrow screens; no horizontal scroll at 390 px width. |
| **Errors** | A move refused by the server appears in a temporary message (3.5 s); the game state is unchanged. |

The server owns the game; the browser only draws the state it receives and sends clicks. The one value
computed in the browser is the hover preview (cosmetic).

### 7.3 Console  🟡

Colored blocks in true color (24-bit ANSI), the cards side by side (current, then the upcoming ones),
status lines for scores, turns left, line streak and rules.
Input: `row col` or `row,col`, 1-based; `q`, `quit` or `exit` quits to home; invalid input is explained and
asked again. Menus: `1) Play  2) Quit`, then `Replay (r) or go back to home page (h)?`.
Limitation: **no settings screen**; the game uses the command-line options (section 9).

---

## 8. Web API

Base: the server root. JSON in and out. Games live **in memory** in the server process.

| Method and path | Request | Response |
|-----------------|---------|----------|
| `GET /api/settings` | none | `{defaults, parameters[], rules[]}`: the configuration defaults, the game parameters (key, label, kind, min, max, step) and each rule (name, enabled, description, options, option specs) |
| `POST /api/games` | optional `{"config": {...}}` (any subset of the configuration dictionary) | **201** and the full game state; **400** `{"detail": "<readable message>"}` if the configuration is invalid |
| `GET /api/games/{id}` | none | the full state; **404** if unknown or expired |
| `POST /api/games/{id}/moves` | `{"row": int, "col": int}` (0-based) | the new full state; **400** if outside the board or the game is over; **404** unknown game; **422** malformed body |
| `DELETE /api/games/{id}` | none | **204**, also if the game does not exist |
| `GET /`, `/static/*` | none | the page and its files |
| `GET /docs` | none | interactive API documentation generated by FastAPI |

Game state fields:

| Field | Type | Meaning |
|-------|------|---------|
| `id` | text | game id |
| `size` | int | board side |
| `players` | list of `{name, color}` | in turn order, color as `#rrggbb` |
| `grid` | list of lists | owner name or `null` per cell |
| `current_player` | text | name |
| `scores` | object | name → cells owned |
| `turns_left`, `total_turns` | int | |
| `is_over` | bool | |
| `winner` | text or null | the single winner, null if tied or not over |
| `winners` | list of text | everybody at the top when over, else empty |
| `outcome` | text or null | "X wins!", "It's a draw!"... when over |
| `current_card` | `{size, offsets, note}` | offsets are `[d_row, d_col]` from the center; `note` set by a rule or empty |
| `upcoming_cards` | list of cards | base cards, no note |
| `line_streak`, `line_streak_limit` | int, int or null | limit is null when `line_streak_wipe` is off |
| `rules` | list of text | rules in force, in execution order |
| `config` | object | the game's configuration dictionary |
| `last_move` | object or null | `player`, `next_player`, `row`, `col`, `changed`, `new_lines`, `bonus_turn`, `events` (codes), `line_streak`, `message` (lines) |
| `message` | list of text | what to display under the board |

| ID | Requirement |
|----|-------------|
| **WB-1** | Each game is created with its own configuration; the server's default configuration (from the command line) fills in anything not sent. |
| **WB-2** | Requests on the same game are serialized by a lock; games are independent. |
| **WB-3** | The store keeps at most **500** games (most recently used kept); older ones are dropped and answer 404. |
| **WB-4** | The server has no authentication and must run as a **single process**. |

Status: ✅ (tests: `test_web.py`, browser test).

---

## 9. Command line

```
python main.py [--ui pygame|cmd|web] [--host H] [--port P]
               [--players N] [--board-size N] [--turns N]
               [--list-rules] [--only RULES] [--enable RULES] [--disable RULES]
               [--set RULE.OPTION=VALUE]
```

| ID | Requirement |
|----|-------------|
| **CL-1** | Default interface is `pygame`. A missing optional dependency gives a one-line instruction, not a stack trace. |
| **CL-2** | `--players`, `--board-size`, `--turns` set the **starting values** of a game (the pygame and web screens start from them; the console uses them directly). |
| **CL-3** | Rules: `--list-rules` prints every rule with `[x]`/`[ ]`, its options and description, then exits. `--only a,b` turns on only those (`none` = no rule). `--enable` and `--disable` take comma-separated names and may be repeated. `--set rule.option=value` changes an option. |
| **CL-4** | Invalid values (unknown rule or option, players out of range...) stop the program with a readable usage error before any interface starts. |
| **CL-5** | `--host` (default 127.0.0.1) and `--port` (default 8000) apply to `--ui web`. |

---

## 10. Non-functional requirements

| ID | Requirement | Status |
|----|-------------|--------|
| **NF-1** | Python ≥ 3.9. Core, console and tests need no dependency besides pytest. | ✅ |
| **NF-2** | Optional dependencies: `pygame ≥ 2.5` (pygame interface), `fastapi ≥ 0.110` and `uvicorn ≥ 0.27` (website), `httpx ≥ 0.27` (web tests). pygame audio is not initialised. | ✅ |
| **NF-3** | Determinism: with a fixed card source, a game is fully reproducible. | ✅ |
| **NF-4** | The core is free of I/O and can run on a server; the browser never holds game rules. | ✅ |
| **NF-5** | No persistence: games disappear when the program or server stops. | 🟡 |
| **NF-6** | No security features (accounts, rate limits, TLS). Suitable for a local machine, a LAN or a demo. | 🟡 |
| **NF-7** | Layout targets: pygame 860 x 700; website from 390 px (phone) to desktop. | ✅ |

---

## 11. Verification

| Suite | Tests | Covers |
|-------|------:|--------|
| `tests/test_board.py` | 6 | painting, bounds, lines, snapshot, comparison by value |
| `tests/test_card.py` | 11 | card geometry, random cards, `with_line`, `with_neutral_center`, notes |
| `tests/test_game.py` | 10 | stamping, clipping, overwriting, shared turns, winner, validation |
| `tests/test_rule_units.py` | 23 | **each rule alone** with a hand-made context |
| `tests/test_ruleset.py` | 13 | on/off switches, options, validation, order, dictionary form |
| `tests/test_game_rules.py` | 36 | rules in a game: each alone, combinations, precedence, catch-up, grid coverage, several players, custom rules, all 32 on/off combinations in random games |
| `tests/test_config.py` | 24 | players, validation, dictionary form with error messages, settings schema vs core |
| `tests/test_messages.py` | 5 | shared wording, placeholders, outcomes |
| `tests/test_match_runner.py`, `test_application.py` | 6 + 7 | glue: selectors for N players, per-game settings, replay, back |
| `tests/test_cmd.py` | 11 | console interface, command-line switches, full scripted match |
| `tests/test_pygame_ui.py` | 21 | layout, menus, **settings screen**, 2 to 6 players drawing, full 3-player flow (headless) |
| `tests/test_web.py` | 22 | the API: per-game config and its errors, 3 players, rules, schema, eviction, static files |
| **Total** | **195** | |
| `tests/e2e_browser/e2e.mjs` | 37 checks | the real website in headless Chrome: form, play, hover, penalties, 3-player rotation, replay, defaults, refused config, reload-resume, Esc, a 50-turn match, phone width, no unexpected console errors |

Run: `pytest` (Python), `node e2e.mjs` after starting the web server (browser; Linux uses a bundled
Chromium, other systems set `CHROME_PATH`).

---

## 12. Known limitations

| # | Limitation | Impact |
|---|------------|--------|
| L-1 | All players share one screen (**hot-seat**). No players on different devices, no seat tokens. | Core of "multiplayer" is done; remote play needs a seat check in `GameSession.play` and polling or WebSocket. |
| L-2 | No bots are shipped. The `MoveSelector` interface and the per-player selector mapping exist. | A bot is one class plus one line in `main.py`. |
| L-3 | The console has no settings screen (command-line options only). | Per-game settings in the console need a text menu. |
| L-4 | pygame and web layouts assume **3x3 cards**; `card_size` is not offered in the screens. | Other sizes need new sidebar positions. |
| L-5 | pygame blocks while waiting for a human; closing the window is noticed only while waiting for a human or a menu. | A slow bot would freeze the window (use a thread or poll events). |
| L-6 | Turns are shared: with more players each plays fewer moves. | Raise `total_turns` in the settings (no per-player turn count). |
| L-7 | The palette is fixed at 6 players; names and colors cannot be customized. | |
| L-8 | The pygame score row fits up to 6 players only because names are short. | |
| L-9 | A rule can end the game with a winner or by score; it cannot force a draw. | |
| L-10 | Games and settings are not saved; the web server forgets games on restart and keeps 500 at most. | |
| L-11 | No tie-breaker: ties at the top are reported as a draw among the tied players. | |
| L-12 | Tests print a Starlette deprecation warning about `httpx` (harmless). | |
| L-13 | The pyproject description is generic (version `0.1.0`). | |

---

## 13. Decisions taken where the request left room

| # | Request | Decision |
|---|---------|----------|
| D-1 | "Both players play together 50 turns" | `total_turns` is a single shared counter; bonus moves consume it (GM-9). |
| D-2 | "Fill the whole grid: win immediately and the game ends", then "when the grid is fully covered, the game ends (by one player or by both)" | The rule fires on **no neutral cell left**, regardless of owners; one owner wins; mixed grids are decided by score by default, with a `mover` option for the other reading (RL-20 to RL-23). The previous "flip to opponent" behavior is kept as an alternative rule, off by default. |
| D-3 | "If you fill three consecutive lines (played three consecutive times) you lose all your cells" | A streak is consecutive line-completing moves by the same player (exactly a chain of bonus moves). The turn then passes to the next player. Only the offending player's cells are removed (RL-40 to RL-42). |
| D-4 | Penalty order when two apply | Execution order decides: full-grid rules first, then the wipe, then the bonus (RL-4, RL-5). |
| D-5 | "Difference of more than 10: the trailing player gets a card with a line formed (in addition to the fourth cell); the dominating one always has an empty card (center neutral, still 4 colored cells)" | Strictly more than the gap; the boost card contains a full line plus the extra cell; the handicap card has a neutral center; both derived from the drawn card; applied when a card becomes current; "Coming next" shows base cards (RL-60 to RL-66). "Empty card" was read as "neutral center". |
| D-6 | Several players and the catch-up rule | Each player is compared with the best of the others; handicap only if ahead of everybody (RL-60). |
| D-7 | Several players and the flip rule | The board goes to the next player in turn order (RL-31). |
| D-8 | "Each game has its own configuration", "configurable in pygame as well" | Per-game `GameConfig`, a settings screen in pygame and a form in the website, command-line starting values for all (section 5). |
| D-9 | "Many players, each with a certain color" | 2 to 6 players with a fixed palette (GM-1, GM-2); players on one screen (L-1). |
| D-10 | Bonus on the last turn | None: nothing is left to play (RL-52). |

---

## 14. Extension points

| To... | Do... |
|-------|-------|
| Add a rule | New file in `core/rules/` + one line in `registry.py` (RL-11) |
| Add a game parameter | A field in `GameConfig`, in `to_dict`/`from_dict`, and a line in `SETTINGS`; both screens show it |
| Add a bot, network player, neural network or LLM | Implement `MoveSelector.choose_move(game)` and map it to a player in `main.py` |
| Add an interface (tkinter, pyplot...) | Implement `Renderer`, `Menu` and a human `MoveSelector` in `ui/<name>/`, add a branch in `main.py` |
| Use another card distribution | Implement `CardSource` and use it in the game factory |
| Play from several devices | Seat tokens per player in `SessionStore`, a seat check in `GameSession.play`, polling or WebSocket |

---

## 15. Traceability: where each requirement lives

| Requirements | Code | Tests |
|--------------|------|-------|
| GM-1 to GM-15 | `core/game.py`, `core/board.py`, `core/card.py`, `core/models.py` | `test_game.py`, `test_board.py`, `test_card.py`, `test_game_rules.py` |
| RL-1 to RL-11 | `core/rules/base.py`, `core/rules/ruleset.py`, `core/rules/registry.py` | `test_rule_units.py`, `test_ruleset.py` |
| RL-20 to RL-23 | `core/rules/full_board_win.py` | `test_rule_units.py`, `test_game_rules.py`, `test_web.py` |
| RL-30 to RL-32 | `core/rules/full_board_flip.py` | `test_rule_units.py`, `test_game_rules.py` |
| RL-40 to RL-42 | `core/rules/line_streak_wipe.py`, streak in `core/game.py` | `test_rule_units.py`, `test_game_rules.py` |
| RL-50 to RL-52 | `core/rules/line_bonus.py` | `test_rule_units.py`, `test_game_rules.py` |
| RL-60 to RL-66 | `core/rules/catch_up_cards.py`, `core/card.py` | `test_rule_units.py`, `test_card.py`, `test_game_rules.py` |
| CF-1 to CF-6 | `core/config.py`, `core/rules/ruleset.py` | `test_config.py`, `test_ruleset.py`, `test_application.py` |
| AR-1 to AR-7 | `core/game.py`, `match_runner.py`, `application.py`, `players/base.py` | `test_match_runner.py`, `test_application.py` |
| Section 7.1 | `ui/pygame_ui/` | `test_pygame_ui.py` |
| Section 7.2, 8 | `ui/web/` | `test_web.py`, `tests/e2e_browser/e2e.mjs` |
| Section 7.3 | `ui/cmd/` | `test_cmd.py` |
| CL-1 to CL-5 | `main.py` | `test_cmd.py`, `test_web.py` |