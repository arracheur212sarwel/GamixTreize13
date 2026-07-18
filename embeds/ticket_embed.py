"""
embeds/ticket_embed.py
Portage Python de TicketGMT/src/embeds/ticketEmbed.js
"""

import discord

import config


def _color(value: str) -> int:
    return int(value.strip("#"), 16)


def base_embed() -> discord.Embed:
    embed = discord.Embed(color=_color(config.TICKET_EMBED_COLOR))
    embed.set_footer(text=config.TICKET_FOOTER)
    embed.timestamp = discord.utils.utcnow()
    return embed


def setup_embed() -> discord.Embed:
    embed = base_embed()
    embed.title = "🎫 Centre de support"
    embed.description = (
        "Besoin d'aide ? Clique sur le bouton ci-dessous pour ouvrir un ticket.\n"
        "Un membre du staff te répondra dès que possible."
    )
    return embed


def welcome_embed(user: discord.abc.User, category_label: str) -> discord.Embed:
    embed = base_embed()
    embed.title = "Support"
    embed.description = (
        f"Bienvenue {user.mention} !\n\n"
        f"**Catégorie :** {category_label}\n\n"
        f"Explique ton problème en détail.\n"
        f"Un membre du staff arrivera rapidement."
    )
    embed.set_thumbnail(url=user.display_avatar.url)
    return embed


def closed_embed(closed_by: discord.abc.User) -> discord.Embed:
    embed = base_embed()
    embed.title = "🔒 Ticket fermé"
    embed.description = f"Ce ticket a été fermé par {closed_by.mention}.\nUn staff peut le réouvrir si nécessaire."
    embed.color = _color("#ED4245")
    return embed


def add_claimed_field(embed: discord.Embed, staff_member: discord.abc.User) -> discord.Embed:
    """Ajoute / met à jour le champ 'Pris en charge par' sur l'embed d'accueil du ticket."""
    new_embed = embed.copy()
    fields = [f for f in new_embed.fields if f.name != "Pris en charge par"]
    new_embed.clear_fields()
    for f in fields:
        new_embed.add_field(name=f.name, value=f.value, inline=f.inline)
    new_embed.add_field(name="Pris en charge par", value=staff_member.mention, inline=True)
    return new_embed


TITLES = {
    "create": "🟢 Ticket créé",
    "close": "🔒 Ticket fermé",
    "reopen": "🔓 Ticket réouvert",
    "delete": "🗑️ Ticket supprimé",
    "addMember": "👤 Membre ajouté",
    "claim": "🙋 Ticket pris en charge",
    "rename": "✏️ Ticket renommé",
}


def log_embed(action: str, user: discord.abc.User, ticket_channel_id: int, extra: str = None) -> discord.Embed:
    embed = base_embed()
    embed.title = TITLES.get(action, "Log ticket")
    embed.add_field(name="Utilisateur", value=user.mention, inline=True)
    embed.add_field(name="Ticket", value=f"<#{ticket_channel_id}>" if ticket_channel_id else "N/A", inline=True)
    embed.add_field(name="Date", value=f"<t:{int(discord.utils.utcnow().timestamp())}:F>", inline=False)
    if extra:
        embed.add_field(name="Détails", value=extra, inline=False)
    return embed


def error_embed(message: str) -> discord.Embed:
    embed = base_embed()
    embed.title = "❌ Erreur"
    embed.description = message
    embed.color = _color("#ED4245")
    return embed
