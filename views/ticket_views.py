"""
views/ticket_views.py
Portage Python des boutons/select/modal de TicketGMT
(src/buttons/*.js, src/selects/*.js, src/modals/*.js).

Toutes les vues sont persistantes (timeout=None, custom_id fixes) et sont
réenregistrées au démarrage du bot dans main.py via bot.add_view(), à
l'exception du menu de sélection de catégorie qui n'accompagne qu'une
réponse éphémère de courte durée.
"""

import re

import discord

import config
from embeds.ticket_embed import error_embed
from utils.permissions import is_staff



class TicketPanelView(discord.ui.View):
    """Bouton persistant 'Créer un ticket' envoyé par /setup-ticket."""

    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Créer un ticket", emoji="🎫", style=discord.ButtonStyle.primary, custom_id="ticket_create_panel")
    async def create_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
        options = [
            discord.SelectOption(label=cat.get("label", key), value=key, emoji=cat.get("emoji") or None)
            for key, cat in config.TICKET_CATEGORIES.items()
        ]
        if not options:
            return await interaction.response.send_message("❌ Aucune catégorie de ticket n'est configurée.", ephemeral=True)

        view = TicketCategorySelectView(options)
        await interaction.response.send_message(
            "Sélectionne la catégorie correspondant à ta demande :", view=view, ephemeral=True
        )


class TicketCategorySelectView(discord.ui.View):
    def __init__(self, options):
        super().__init__(timeout=300)
        self.add_item(TicketCategorySelect(options))


class TicketCategorySelect(discord.ui.Select):
    def __init__(self, options):
        super().__init__(placeholder="Choisis une catégorie...", options=options, custom_id="ticket_category_select")

    async def callback(self, interaction: discord.Interaction):
        from utils.ticket_manager import create_ticket_channel

        await interaction.response.defer()
        category_key = self.values[0]
        result = await create_ticket_channel(interaction, category_key)

        if result.get("error"):
            return await interaction.edit_original_response(content=None, embed=error_embed(result["error"]), view=None)

        channel = result["channel"]
        await interaction.edit_original_response(content=f"✅ Ton ticket a été créé : {channel.mention}", embed=None, view=None)



class TicketOpenView(discord.ui.View):
    """Boutons affichés sur un ticket ouvert : prendre en charge / ajouter un membre / fermer."""

    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Prendre en charge", emoji="🙋", style=discord.ButtonStyle.primary, custom_id="ticket_claim")
    async def claim(self, interaction: discord.Interaction, button: discord.ui.Button):
        from utils.ticket_manager import claim_ticket

        if not is_staff(interaction.user):
            return await interaction.response.send_message(
                embed=error_embed("Seul le staff peut prendre en charge un ticket."), ephemeral=True
            )

        result = await claim_ticket(interaction)
        if result.get("error"):
            return await interaction.response.send_message(embed=error_embed(result["error"]), ephemeral=True)

        if result.get("new_embed"):
            await interaction.response.edit_message(embed=result["new_embed"])
        else:
            await interaction.response.send_message(content=f"🙋 Ticket pris en charge par {interaction.user.mention}.")

    @discord.ui.button(label="Ajouter un membre", emoji="👤", style=discord.ButtonStyle.secondary, custom_id="ticket_add_member")
    async def add_member(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not is_staff(interaction.user):
            return await interaction.response.send_message(
                embed=error_embed("Seul le staff peut ajouter un membre au ticket."), ephemeral=True
            )
        await interaction.response.send_modal(AddMemberModal())

    @discord.ui.button(label="Fermer", emoji="🔒", style=discord.ButtonStyle.danger, custom_id="ticket_close")
    async def close(self, interaction: discord.Interaction, button: discord.ui.Button):
        from utils.ticket_manager import close_ticket

        if not is_staff(interaction.user):
            return await interaction.response.send_message(embed=error_embed("Seul le staff peut fermer un ticket."), ephemeral=True)

        await interaction.response.defer(ephemeral=True)
        result = await close_ticket(interaction)
        if result.get("error"):
            return await interaction.followup.send(embed=error_embed(result["error"]))
        await interaction.followup.send(content="🔒 Ticket fermé.")


class TicketClosedView(discord.ui.View):
    """Boutons affichés sur un ticket fermé : réouvrir / supprimer."""

    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Réouvrir", emoji="🔓", style=discord.ButtonStyle.success, custom_id="ticket_reopen")
    async def reopen(self, interaction: discord.Interaction, button: discord.ui.Button):
        from utils.ticket_manager import reopen_ticket

        if not is_staff(interaction.user):
            return await interaction.response.send_message(embed=error_embed("Seul le staff peut réouvrir un ticket."), ephemeral=True)

        await interaction.response.defer(ephemeral=True)
        result = await reopen_ticket(interaction)
        if result.get("error"):
            return await interaction.followup.send(embed=error_embed(result["error"]))
        await interaction.followup.send(content="🔓 Ticket réouvert.")

    @discord.ui.button(label="Supprimer", emoji="🗑️", style=discord.ButtonStyle.danger, custom_id="ticket_delete")
    async def delete(self, interaction: discord.Interaction, button: discord.ui.Button):
        from utils.ticket_manager import delete_ticket

        if not is_staff(interaction.user):
            return await interaction.response.send_message(embed=error_embed("Seul le staff peut supprimer un ticket."), ephemeral=True)

        await interaction.response.defer()
        result = await delete_ticket(interaction)
        if result.get("error"):
            return await interaction.followup.send(embed=error_embed(result["error"]))
        await interaction.followup.send(content="🗑️ Suppression en cours...")



class AddMemberModal(discord.ui.Modal, title="Ajouter un membre"):
    user_id_input = discord.ui.TextInput(label="ID utilisateur", placeholder="Ex: 123456789012345678", required=True)

    async def on_submit(self, interaction: discord.Interaction):
        from utils.ticket_manager import add_member

        raw_id = self.user_id_input.value.strip()
        if not re.match(r"^\d{15,25}$", raw_id):
            return await interaction.response.send_message(
                embed=error_embed("L'ID fourni n'est pas valide. Il doit être uniquement composé de chiffres."), ephemeral=True
            )

        await interaction.response.defer(ephemeral=True)
        result = await add_member(interaction, int(raw_id))
        if result.get("error"):
            return await interaction.followup.send(embed=error_embed(result["error"]))
        await interaction.followup.send(content=f"✅ {result['target_member'].mention} a été ajouté au ticket.")
