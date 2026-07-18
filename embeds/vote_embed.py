"""
embeds/vote_embed.py
Construction de l'embed "Smash or Pass" (partagée entre le cog smashorpass
et la vue de vote pour éviter la duplication).
"""

from datetime import datetime

import discord


def build_vote_embed(smash_count: int, pass_count: int, end_at: datetime, closed: bool = False) -> discord.Embed:
    total = smash_count + pass_count
    smash_pct = round((smash_count / total) * 100) if total else 0
    pass_pct = round((pass_count / total) * 100) if total else 0

    title = "🔒 Vote terminé" if closed else "📊 Smash or Pass"
    color = discord.Color.dark_grey() if closed else discord.Color.from_rgb(255, 105, 150)

    embed = discord.Embed(title=title, color=color)
    embed.add_field(name="❤️ Smash", value=f"{smash_count} ({smash_pct}%)", inline=True)
    embed.add_field(name="❌ Pass", value=f"{pass_count} ({pass_pct}%)", inline=True)
    embed.add_field(name="👥 Votes", value=str(total), inline=True)

    end_ts = int(end_at.timestamp())
    if closed:
        embed.add_field(name="⏳ Statut", value=f"Terminé <t:{end_ts}:R>", inline=False)
    else:
        embed.add_field(name="⏳ Fin", value=f"<t:{end_ts}:R>", inline=False)

    return embed
