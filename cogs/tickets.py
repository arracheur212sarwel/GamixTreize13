"""
cogs/tickets.py
Portage Python de TicketGMT (src/commands/setup-ticket.js, src/commands/rename.js).
Les boutons/select/modal persistants sont dans views/ticket_views.py et
réenregistrés une fois au démarrage dans main.py.
"""

import discord
from discord import app_commands
from discord.ext import commands

from embeds.ticket_embed import setup_embed, error_embed
from utils.permissions import is_staff
from utils.ticket_manager import rename_ticket
from views.ticket_views import TicketPanelView


class Tickets(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="setup-ticket", description="Envoie le panneau de création de tickets dans ce salon.")
    @app_commands.default_permissions(administrator=True)
    async def setup_ticket(self, interaction: discord.Interaction):
        if not interaction.user.guild_permissions.administrator:
            return await interaction.response.send_message(
                embed=error_embed("Seuls les administrateurs peuvent utiliser cette commande."), ephemeral=True
            )

        embed = setup_embed()
        await interaction.channel.send(embed=embed, view=TicketPanelView())
        await interaction.response.send_message(content="✅ Panneau de tickets envoyé.", ephemeral=True)

    @app_commands.command(name="rename-ticket", description="Renomme le ticket actuel.")
    @app_commands.describe(nom="Nouveau nom du ticket")
    async def rename(self, interaction: discord.Interaction, nom: str):
        if not is_staff(interaction.user):
            return await interaction.response.send_message(
                embed=error_embed("Tu n'as pas la permission d'utiliser cette commande."), ephemeral=True
            )

        result = await rename_ticket(interaction, nom)
        if result.get("error"):
            return await interaction.response.send_message(embed=error_embed(result["error"]), ephemeral=True)

        await interaction.response.send_message(content=f"✅ Ticket renommé en `{result['new_name']}`.", ephemeral=True)


async def setup(bot: commands.Bot):
    await bot.add_cog(Tickets(bot))
