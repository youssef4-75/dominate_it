"""Rule `catch_up_cards`: the trailing player gets better cards, the leader worse ones."""
from __future__ import annotations

from typing import TYPE_CHECKING

from core.rules.base import CardContext, Option, Rule

if TYPE_CHECKING:
    from core.card import Card


class CatchUpCards(Rule):
    name = "catch_up_cards"
    description = (
        "A player is compared with the best of the OTHER players. More than `gap` cells behind: "
        "the card contains a full line (plus the extra cell). More than `gap` cells ahead of "
        "everybody: the card has a neutral center."
    )
    options_spec = {"gap": Option(10, "Cells of difference", minimum=0, maximum=100)}

    def adjust_card(self, card: "Card", ctx: CardContext) -> "Card":
        best_other = max(ctx.scores[p] for p in ctx.players if p != ctx.player)
        lead = ctx.scores[ctx.player] - best_other
        gap = self.option("gap")
        if lead > gap:
            return card.with_neutral_center().with_note(
                "Leader handicap: the center of this card is neutral."
            )
        if lead < -gap:
            return card.with_line().with_note("Catch-up boost: this card contains a full line!")
        return card
