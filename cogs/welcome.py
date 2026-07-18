import discord
from discord.ext import commands

import config


class Welcome(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        if config.WELCOME_ROLE_ID:
            role = member.guild.get_role(config.WELCOME_ROLE_ID)
            if role:
                try:
                    await member.add_roles(role, reason="Rôle automatique à l'arrivée")
                except discord.HTTPException:
                    self.bot.logger.warning("Impossible d'ajouter le rôle de bienvenue à %s", member)

        if not config.WELCOME_CHANNEL_ID:
            return

        channel = member.guild.get_channel(config.WELCOME_CHANNEL_ID)
        if not channel:
            return

        embed = discord.Embed(
            title="Bienvenue",
            description=f"sur le serveur Discord **Chez Malika**",
            color=discord.Color.from_rgb(88, 101, 242),
        )
        embed.set_thumbnail(url=member.display_avatar.url)
        embed.set_footer(text=f"Membre n°{member.guild.member_count}")
        embed.timestamp = discord.utils.utcnow()

        try:
            await channel.send(content=f"🎉 Bienvenue {member.mention} chez Malika ! 🎉", embed=embed)
        except discord.HTTPException:
            self.bot.logger.warning("Impossible d'envoyer le message de bienvenue dans %s", channel)


async def setup(bot: commands.Bot):
    await bot.add_cog(Welcome(bot))