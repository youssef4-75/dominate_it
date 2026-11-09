# Grid Color War: Gameplay Guide

A turn-based strategy game for 2 to 6 players on one screen (hot-seat).
You stamp colored **cards** onto a **grid**. When the game ends, the player
who owns the most cells wins.

This guide is for players. For the architecture, see `SPECIFICATION.md`.

---

## 1. The goal

Own the **most cells** when the game ends.

The game ends when either:

- the **shared turn counter** runs out (30 turns by default), or
- a rule ends it early (see `full_board_win` below).

If several players tie for the most cells, it is a **draw** among them.

---

## 2. One turn, step by step

1. A **current card** is dealt. It is a 3x3 pattern with 4 colored cells,
  always in the color of the player whose turn it is.
2. You can see the **next 2 cards** or more based on the settings in "Coming next".
3. The current player **clicks a board cell**.
4. The **center of the card** lands on that cell, and every colored card cell
  **overwrites** the owner of the board cell beneath it.
5. Cells of the card that fall **outside the board are ignored** (clipped).
  You can play on edges and corners.
6. The turn passes to the next player, unless a rule grants a **bonus turn**.

**Turns are shared.** With 4 players and 50 turns, each player plays about 12
moves. If you want longer games, raise `total_turns` in the settings.

---

## 3. Moves you can make

There is only one kind of move (stamp the card), but these are your real choices:


| Choice                             | When to use it                                                                                     |
| ---------------------------------- | -------------------------------------------------------------------------------------------------- |
| **Overwrite an opponent**          | Deny them cells and flip the score in one move.                                                    |
| **Grow your own block**            | Build toward a full row, column or diagonal.                                                       |
| **Complete a line**                | Triggers `line_bonus`: you play again immediately.                                                 |
| **Play on an edge**                | The card is clipped, so you place fewer cells, but you can still complete a line along the border. |
| **Play the center of the board**   | High value early: the center touches more future lines than corners.                               |
| **Avoid a third consecutive line** | If `line_streak_wipe` is on, completing a line on 3 consecutive moves wipes **all your cells**.    |


**Important:** a move after the game is over is refused and changes nothing.
A move outside the board is refused. Invalid input is explained, not silently
ignored.

---

## 4. The five rules (and what they change)

Every rule is **switchable per game** in the settings screen (pygame and web),
or with command-line switches. Defaults are in **bold**.

### `full_board_win` (**on**)

The moment **no cell is neutral** any more, the game ends immediately.

- If one player owns every cell, that player wins.
- If several players cover the grid, the player with the most cells wins
(default `winner=most_cells`), or the player who filled the **last** neutral
cell wins if `winner=mover`.

**Watch out:** you can be ahead and still lose if someone else fills the last
cell and `winner=mover` is set.

### `line_bonus` (**on**)

Completing a **new** full line (row, column, or diagonal if enabled) gives you
**another move**.

- Only a *new* line counts. A line you already owned does not count again.
- **No bonus on the very last turn**, and no bonus after a penalty.

### `line_streak_wipe` (**on**, limit 3)

Completing a line on **3 consecutive moves** (a streak) **wipes all your
cells**: they become neutral, and the next player plays.

- Only your cells are removed. Your opponents keep theirs.
- A streak is broken by any move that completes no new line, or by the turn
passing to someone else.

**Watch out:** `line_bonus` and `line_streak_wipe` work together. Your bonus
turns are exactly what builds a streak. Two lines in a row is powerful; the
third can cost you the game.

### `catch_up_cards` (**on**, gap 10)

The game compares you with the **best of the other players**.

- **More than 10 cells behind:** your card is replaced by one containing a
**full line** (still 4 colored cells). A comeback tool.
- **More than 10 cells ahead of everybody:** your card gets a **neutral
center** (still 4 colored cells). A handicap for the leader.
- Exactly 10 changes nothing. "Coming next" shows the **base** cards; the
adjustment happens only when the card becomes current.

**Watch out:** if you are far ahead, your cards get worse. A big lead is not
safe.

### `full_board_flip` (off by default)

If you color the **whole grid** with your color in one move, every cell goes to
the **next player**, who then plays.

- A move that changes nothing on an already single-colored board does not
trigger it.
- It can trigger on the last turn.

**Watch out:** this is a trap. Filling the board alone hands your work to your
opponent. Leave one cell to someone else, or make sure the flip helps you. This 
rule and the **full_board_win** cancel each other, if that one is active, this rule 
is ignored.

---

## 5. Rule precedence (when several rules apply)

The rules run in this fixed order, and the **first one that decides the move
stops the rest**:

1. `full_board_win`
2. `full_board_flip`
3. `line_streak_wipe`
4. `line_bonus`

Practical consequences:

- If `full_board_win` and `full_board_flip` are both on, **the win happens**
and the flip never does.
- A move that triggers the **wipe** never gets a **bonus turn**.

---

## 6. Parameters you can change

Change these **before each game** in the settings screen (pygame: Play →
Game settings; web: the home form). In the console, use the command-line
options (there is no settings screen there).


| Parameter                    | Range (screens)    | Default       | What it does                                                                                      |
| ---------------------------- | ------------------ | ------------- | ------------------------------------------------------------------------------------------------- |
| **Players**                  | 2 to 6             | 2             | Number of players. The order is the turn order. Colors: RED, BLUE, GREEN, YELLOW, PURPLE, ORANGE. |
| **Board size**               | 3 to 9             | 5             | The board is size x size.                                                                         |
| **Turns (shared)**           | 5 to 500, step 5   | 30            | Total moves of **all** players together. Bonus moves consume one.                                 |
| **Colored cells per card**   | 1 to 9             | 4             | How many cells of the 3x3 card are colored. More cells = more coverage per move.                  |
| **Cards shown ahead**        | 0 to 3             | 1             | How many upcoming cards you see. 0 = no preview.                                                  |
| **Diagonals count as lines** | on / off           | off           | Whether diagonals count for `line_bonus` and `line_streak_wipe`.                                  |
| **Each rule**                | on / off + options | see section 4 | Switch rules and change their options (`winner`, `limit`, `gap`).                                 |


Command-line equivalents (for the console, or to set the starting values of the
other screens):

```bash
python main.py --players 4 --board-size 7 --turns 80
python main.py --list-rules
python main.py --only line_bonus
python main.py --only none
python main.py --disable catch_up_cards
python main.py --enable full_board_flip --disable full_board_win
python main.py --set line_streak_wipe.limit=2
python main.py --set catch_up_cards.gap=5
python main.py --set full_board_win.winner=mover
```

