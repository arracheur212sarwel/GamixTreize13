"""
views/vote_view.py
Vue (discord.ui.View) attachée à l'embed de vote de chaque publication.

Les custom_id des boutons embarquent le message_id de la publication
(ex: "smashpass:smash:123456789") afin que la vue reste fonctionnelle
après un redémarrage du bot : main.py réenregistre une instance de cette
vue pour chaque publication encore active au démarrage via bot.add_view().
"""

from datetime import datetime

import discord

import database
from embeds.vote_embed import build_vote_embed


class VoteView(discord.ui.View):
    def __init__(self, message_id: int, disabled: bool = False):
        super().__init__(timeout=None)
        self.message_id = message_id

        self.smash_button.custom_id = f"smashpass:smash:{message_id}"
        self.pass_button.custom_id = f"smashpass:pass:{message_id}"

        if disabled:
            self.smash_button.disabled = True
            self.pass_button.disabled = True

    async def _handle_vote(self, interaction: discord.Interaction, vote: str):
        post = await database.sop_get_post(self.message_id)

        if post is None or post["closed"]:
            await interaction.response.send_message("⏳ Ce vote est terminé, tu ne peux plus voter.", ephemeral=True)
            return

        current_vote = await database.sop_get_user_vote(self.message_id, interaction.user.id)

        if current_vote == vote:
            await interaction.response.defer()
            return

        await database.sop_set_vote(self.message_id, interaction.user.id, vote)

        counts = await database.sop_get_vote_counts(self.message_id)
        end_at = datetime.fromisoformat(post["end_at"])
        embed = build_vote_embed(counts["smash"], counts["pass"], end_at)

        await interaction.response.edit_message(embed=embed, view=self)

    @discord.ui.button(label="Smash", emoji="❤️", style=discord.ButtonStyle.success, custom_id="smashpass:smash:placeholder")
    async def smash_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self._handle_vote(interaction, "smash")

    @discord.ui.button(label="Pass", emoji="❌", style=discord.ButtonStyle.danger, custom_id="smashpass:pass:placeholder")
    async def pass_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self._handle_vote(interaction, "pass")
