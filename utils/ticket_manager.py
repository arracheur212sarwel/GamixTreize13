"""
utils/ticket_manager.py
Portage Python de TicketGMT/src/utils/ticketManager.js
"""

import asyncio
import re
import unicodedata

import discord

import config
import database
from embeds.ticket_embed import welcome_embed, closed_embed, add_claimed_field
from utils.ticket_logger import log_ticket_event
from utils.transcript import generate_and_send_transcript


def sanitize_username(username: str) -> str:
    normalized = unicodedata.normalize("NFD", username.lower())
    no_accents = "".join(c for c in normalized if unicodedata.category(c) != "Mn")
    cleaned = re.sub(r"[^a-z0-9]", "-", no_accents)
    cleaned = re.sub(r"-+", "-", cleaned).strip("-")
    return cleaned[:20] or "user"


def open_ticket_buttons_row(status: str = "open") -> discord.ui.View:
    from views.ticket_views import TicketOpenView, TicketClosedView

    return TicketOpenView() if status == "open" else TicketClosedView()


async def create_ticket_channel(interaction: discord.Interaction, category_key: str):
    guild = interaction.guild
    user = interaction.user
    client = interaction.client

    existing = await database.ticket_get_open_by_owner(user.id, guild.id)
    if existing:
        channel = guild.get_channel(existing["channel_id"])
        suffix = f" : {channel.mention}" if channel else ""
        return {"error": f"Tu as déjà un ticket ouvert{suffix}. Ferme-le avant d'en ouvrir un nouveau."}

    if await database.ticket_is_on_cooldown(user.id):
        remaining = -(-(await database.ticket_get_remaining_cooldown(user.id)) // 1000)
        return {"error": f"Merci de patienter encore **{remaining}s** avant de créer un nouveau ticket."}

    category_config = config.TICKET_CATEGORIES.get(category_key)
    if not category_config:
        return {"error": "Catégorie de ticket invalide ou mal configurée."}

    parent = None
    category_id = category_config.get("categoryId")
    if category_id:
        parent = guild.get_channel(int(category_id))
        if not isinstance(parent, discord.CategoryChannel):
            parent = None

    staff_role = guild.get_role(config.TICKET_STAFF_ROLE) if config.TICKET_STAFF_ROLE else None

    overwrites = {
        guild.default_role: discord.PermissionOverwrite(view_channel=False),
        user: discord.PermissionOverwrite(view_channel=True, send_messages=True, read_message_history=True, attach_files=True),
        guild.me: discord.PermissionOverwrite(view_channel=True, send_messages=True, manage_channels=True),
    }
    if staff_role:
        overwrites[staff_role] = discord.PermissionOverwrite(view_channel=True, send_messages=True, read_message_history=True)

    label = category_config.get("label", category_key)
    try:
        channel = await guild.create_text_channel(
            name=f"{config.TICKET_NAME_PREFIX}-{sanitize_username(user.name)}",
            category=parent,
            overwrites=overwrites,
            topic=f"Ticket de {user} ({user.id}) | Catégorie: {label}",
            reason=f"Ticket créé par {user}",
        )
    except discord.HTTPException:
        return {"error": "Impossible de créer le salon du ticket (permissions du bot insuffisantes ?)."}

    await database.ticket_create(channel.id, guild.id, user.id, category_key)
    await database.ticket_set_cooldown(user.id, config.TICKET_CREATE_COOLDOWN_SECONDS * 1000)

    category_label = f"{category_config.get('emoji', '')} {label}".strip()
    embed = welcome_embed(user, category_label)
    content = f"{user.mention} {staff_role.mention if staff_role else ''}".strip()
    await channel.send(content=content, embed=embed, view=open_ticket_buttons_row("open"))

    await log_ticket_event(client, "create", user, channel.id)

    return {"channel": channel}


async def close_ticket(interaction: discord.Interaction):
    channel = interaction.channel
    member = interaction.user
    client = interaction.client

    ticket = await database.ticket_get(channel.id)
    if not ticket:
        return {"error": "Ce salon n'est pas un ticket."}
    if ticket["status"] == "closed":
        return {"error": "Ce ticket est déjà fermé."}

    await database.ticket_close(channel.id)

    owner = channel.guild.get_member(ticket["owner_id"])
    if owner:
        try:
            await channel.set_permissions(owner, overwrite=discord.PermissionOverwrite(send_messages=False))
        except discord.HTTPException:
            pass

    embed = closed_embed(member)
    await channel.send(embed=embed, view=open_ticket_buttons_row("closed"))

    await log_ticket_event(client, "close", member, channel.id)
    return {"ok": True}


async def reopen_ticket(interaction: discord.Interaction):
    channel = interaction.channel
    member = interaction.user
    client = interaction.client

    ticket = await database.ticket_get(channel.id)
    if not ticket:
        return {"error": "Ce salon n'est pas un ticket."}
    if ticket["status"] == "open":
        return {"error": "Ce ticket est déjà ouvert."}

    await database.ticket_reopen(channel.id)

    owner = channel.guild.get_member(ticket["owner_id"])
    if owner:
        try:
            await channel.set_permissions(owner, overwrite=discord.PermissionOverwrite(send_messages=True))
        except discord.HTTPException:
            pass

    await channel.send(content=f"🔓 Le ticket a été réouvert par {member.mention}.", view=open_ticket_buttons_row("open"))

    await log_ticket_event(client, "reopen", member, channel.id)
    return {"ok": True}


async def delete_ticket(interaction: discord.Interaction):
    channel = interaction.channel
    member = interaction.user
    client = interaction.client

    ticket = await database.ticket_get(channel.id)
    if not ticket:
        return {"error": "Ce salon n'est pas un ticket."}

    await log_ticket_event(client, "delete", member, channel.id)

    await generate_and_send_transcript(channel, ticket["owner_id"], client)

    delay = config.TICKET_CLOSE_DELETE_DELAY_SECONDS
    try:
        await channel.send(f"🗑️ Ce ticket va être supprimé dans {delay} secondes...")
    except discord.HTTPException:
        pass

    await database.ticket_delete(channel.id)

    async def _delayed_delete():
        await asyncio.sleep(delay)
        try:
            await channel.delete(reason=f"Ticket supprimé par {member}")
        except discord.HTTPException:
            pass

    asyncio.create_task(_delayed_delete())

    return {"ok": True}


async def claim_ticket(interaction: discord.Interaction):
    channel = interaction.channel
    member = interaction.user
    client = interaction.client
    message = interaction.message

    ticket = await database.ticket_get(channel.id)
    if not ticket:
        return {"error": "Ce salon n'est pas un ticket."}
    if ticket["claimed_by"]:
        if ticket["claimed_by"] == member.id:
            return {"error": "Tu as déjà pris en charge ce ticket."}
        return {"error": f"Ce ticket est déjà pris en charge par <@{ticket['claimed_by']}>."}

    await database.ticket_claim(channel.id, member.id)

    new_embed = None
    if message.embeds:
        new_embed = add_claimed_field(message.embeds[0], member)

    await log_ticket_event(client, "claim", member, channel.id)
    return {"ok": True, "new_embed": new_embed}


async def add_member(interaction: discord.Interaction, target_id: int):
    channel = interaction.channel
    member = interaction.user
    client = interaction.client

    ticket = await database.ticket_get(channel.id)
    if not ticket:
        return {"error": "Ce salon n'est pas un ticket."}

    try:
        target_member = await interaction.guild.fetch_member(target_id)
    except discord.NotFound:
        return {"error": "Utilisateur introuvable sur ce serveur. Vérifie l'ID."}

    try:
        await channel.set_permissions(
            target_member, overwrite=discord.PermissionOverwrite(view_channel=True, send_messages=True, read_message_history=True)
        )
    except discord.HTTPException:
        pass

    await channel.send(f"👤 {target_member.mention} a été ajouté au ticket par {member.mention}.")
    await log_ticket_event(client, "addMember", target_member, channel.id, extra=f"Ajouté par {member.mention}")

    return {"ok": True, "target_member": target_member}


async def rename_ticket(interaction: discord.Interaction, new_name: str):
    channel = interaction.channel
    member = interaction.user
    client = interaction.client

    ticket = await database.ticket_get(channel.id)
    if not ticket:
        return {"error": "Ce salon n'est pas un ticket."}

    clean_name = sanitize_username(new_name)
    if not clean_name:
        return {"error": "Nom invalide."}

    try:
        await channel.edit(name=clean_name, reason=f"Renommé par {member}")
    except discord.HTTPException:
        return {"error": "Impossible de renommer ce salon (limite de renommage Discord atteinte ? réessaie dans quelques minutes)."}

    await log_ticket_event(client, "rename", member, channel.id, extra=f"Nouveau nom: {clean_name}")
    return {"ok": True, "new_name": clean_name}
