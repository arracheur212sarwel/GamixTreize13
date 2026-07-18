import discord
from discord.ext import commands

from config import COLOR_SUCCESS, COLOR_WARNING
from database import get_guild_config


class ServerLogs(commands.Cog):
    """Journalise les événements serveur (salons, rôles) dans le salon de logs configuré via /config logs."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    async def get_log_channel(self, guild: discord.Guild):
        cfg = await get_guild_config(guild.id)
        if cfg and cfg["logs_channel"]:
            return guild.get_channel(cfg["logs_channel"])
        return None

    @commands.Cog.listener()
    async def on_guild_channel_create(self, channel):
        log_channel = await self.get_log_channel(channel.guild)
        if log_channel:
            embed = discord.Embed(
                title="📁 Salon créé",
                description=f"**Nom :** {channel.name}\n**Type :** {channel.type}",
                color=COLOR_SUCCESS,
            )
            embed.timestamp = discord.utils.utcnow()
            await log_channel.send(embed=embed)

    @commands.Cog.listener()
    async def on_guild_channel_delete(self, channel):
        log_channel = await self.get_log_channel(channel.guild)
        if log_channel:
            embed = discord.Embed(title="🗑️ Salon supprimé", description=f"**Nom :** {channel.name}", color=COLOR_WARNING)
            embed.timestamp = discord.utils.utcnow()
            await log_channel.send(embed=embed)

    @commands.Cog.listener()
    async def on_member_update(self, before, after):
        log_channel = await self.get_log_channel(after.guild)
        if not log_channel:
            return
        added_roles = [r for r in after.roles if r not in before.roles]
        for role in added_roles:
            embed = discord.Embed(
                title="➕ Rôle ajouté", description=f"{after.mention} a reçu le rôle {role.mention}", color=COLOR_SUCCESS
            )
            embed.timestamp = discord.utils.utcnow()
            await log_channel.send(embed=embed)
        removed_roles = [r for r in before.roles if r not in after.roles]
        for role in removed_roles:
            embed = discord.Embed(
                title="➖ Rôle retiré", description=f"{after.mention} a perdu le rôle {role.mention}", color=COLOR_WARNING
            )
            embed.timestamp = discord.utils.utcnow()
            await log_channel.send(embed=embed)


async def setup(bot: commands.Bot):
    await bot.add_cog(ServerLogs(bot))
