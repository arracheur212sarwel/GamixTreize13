"""
cogs/affinity.py
Suit le temps passé en vocal par membre. Une fois le seuil atteint, envoie
une proposition (avec boutons Valider/Refuser) dans le salon modo, ping
le rôle staff. Aucune attribution automatique : ce sont les modérateurs
qui valident le passage du rôle "nouveau" au rôle "actif".
"""

import time

import discord
from discord import app_commands
from discord.ext import commands, tasks

import config
import database
from utils.permissions import is_staff
from views.affinity_view import AffinityProposalView


class Affinity(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self._initialized = False
        if config.ACTIVE_ROLE_ID and config.MOD_PROPOSAL_CHANNEL_ID:
            self.check_active_sessions.start()

    def cog_unload(self):
        if self.check_active_sessions.is_running():
            self.check_active_sessions.cancel()

    @commands.Cog.listener()
    async def on_ready(self):
        if self._initialized:
            return
        self._initialized = True
        now = int(time.time())
        for guild in self.bot.guilds:
            for vc in guild.voice_channels:
                for member in vc.members:
                    if member.bot:
                        continue
                    row = await database.voice_get_or_create(member.id, guild.id)
                    if not row["session_start"]:
                        await database.voice_start_session(member.id, guild.id, now)
        self.bot.logger.info("Sessions vocales en cours réinitialisées après redémarrage.")

    @commands.Cog.listener()
    async def on_voice_state_update(self, member: discord.Member, before: discord.VoiceState, after: discord.VoiceState):
        if member.bot:
            return
        if not config.ACTIVE_ROLE_ID or not config.MOD_PROPOSAL_CHANNEL_ID:
            return

        now = int(time.time())

        # Entrée en vocal (n'était dans aucun salon avant)
        if before.channel is None and after.channel is not None:
            await database.voice_start_session(member.id, member.guild.id, now)
            return

        # Sortie du vocal (n'est plus dans aucun salon)
        if before.channel is not None and after.channel is None:
            new_total = await database.voice_end_session(member.id, member.guild.id, now)
            if new_total is not None:
                await self._maybe_propose(member, new_total)
            return

        # Changement de salon vocal : la session continue, rien à faire.

    async def _maybe_propose(self, member: discord.Member, total_seconds: int):
        row = await database.voice_get_or_create(member.id, member.guild.id)
        if row["promoted"]:
            return

        threshold_seconds = config.VOICE_ACTIVITY_THRESHOLD_MINUTES * 60
        current_palier = total_seconds // threshold_seconds
        if current_palier < 1 or current_palier <= row["proposal_count"]:
            return

        active_role = member.guild.get_role(config.ACTIVE_ROLE_ID)
        if active_role and active_role in member.roles:
            await database.voice_mark_promoted(member.id, member.guild.id)
            return

        channel = member.guild.get_channel(config.MOD_PROPOSAL_CHANNEL_ID)
        if not channel:
            return

        staff_role = member.guild.get_role(config.TICKET_STAFF_ROLE) if config.TICKET_STAFF_ROLE else None
        hours = total_seconds // 3600
        minutes = (total_seconds % 3600) // 60

        embed = discord.Embed(
            title="🎙️ Proposition de rôle par affinité",
            description=(
                f"{member.mention} a passé **{hours}h{minutes:02d}** en vocal cumulés "
                f"(palier {current_palier} × {config.VOICE_ACTIVITY_THRESHOLD_MINUTES}min).\n"
                f"Faut-il lui donner le rôle actif ?"
            ),
            color=discord.Color.blurple(),
        )
        embed.set_thumbnail(url=member.display_avatar.url)

        content = staff_role.mention if staff_role else ""
        await channel.send(content=content, embed=embed, view=AffinityProposalView(member.id))
        await database.voice_set_proposal_count(member.id, member.guild.id, current_palier)

    @app_commands.command(name="voc", description="Affiche le temps passé en vocal d'un membre")
    @app_commands.describe(membre="Le membre à consulter (toi-même par défaut)")
    async def voc(self, interaction: discord.Interaction, membre: discord.Member = None):
        target = membre or interaction.user

        if target.id != interaction.user.id and not is_staff(interaction.user):
            return await interaction.response.send_message(
                "Tu ne peux consulter que ton propre temps en vocal.", ephemeral=True
            )

        row = await database.voice_get_or_create(target.id, interaction.guild.id)
        total_seconds = row["total_seconds"]

        if row["session_start"]:
            total_seconds += max(0, int(time.time()) - row["session_start"])

        hours = total_seconds // 3600
        minutes = (total_seconds % 3600) // 60

        embed = discord.Embed(
            title=f"🎙️ Temps vocal — {target.display_name}",
            color=discord.Color.blurple(),
        )
        embed.add_field(name="Temps cumulé", value=f"**{hours}h{minutes:02d}**", inline=True)
        embed.add_field(
            name="Statut",
            value="✅ Rôle actif" if row["promoted"] else f"Palier atteint : {row['proposal_count']}",
            inline=True,
        )
        embed.set_thumbnail(url=target.display_avatar.url)

        await interaction.response.send_message(embed=embed, ephemeral=(target.id != interaction.user.id))

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot or not message.guild:
            return
        await database.message_increment(message.author.id, message.guild.id)

    @app_commands.command(name="topvoc", description="Top 3 des membres les plus actifs en vocal")
    async def topvoc(self, interaction: discord.Interaction):
        rows = await database.voice_get_top(interaction.guild.id, limit=3)
        if not rows:
            return await interaction.response.send_message("Aucune donnée pour le moment.", ephemeral=True)

        now = int(time.time())
        medals = ["🥇", "🥈", "🥉"]
        lines = []
        for i, row in enumerate(rows):
            total = row["total_seconds"]
            if row["session_start"]:
                total += max(0, now - row["session_start"])
            hours = total // 3600
            minutes = (total % 3600) // 60
            lines.append(f"{medals[i]} <@{row['user_id']}> — **{hours}h{minutes:02d}**")

        embed = discord.Embed(title="🎙️ Top vocal", description="\n".join(lines), color=discord.Color.blurple())
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="topmsg", description="Top 3 des membres les plus actifs en messages")
    async def topmsg(self, interaction: discord.Interaction):
        rows = await database.message_get_top(interaction.guild.id, limit=3)
        if not rows:
            return await interaction.response.send_message("Aucune donnée pour le moment.", ephemeral=True)

        medals = ["🥇", "🥈", "🥉"]
        lines = [f"{medals[i]} <@{row['user_id']}> — **{row['message_count']}** messages" for i, row in enumerate(rows)]

        embed = discord.Embed(title="💬 Top messages", description="\n".join(lines), color=discord.Color.green())
        await interaction.response.send_message(embed=embed)

    @tasks.loop(minutes=5)
    async def check_active_sessions(self):
        """Filet de sécurité : vérifie aussi les membres encore en vocal (pas seulement à la sortie)."""
        now = int(time.time())
        for guild in self.bot.guilds:
            for vc in guild.voice_channels:
                for member in vc.members:
                    if member.bot:
                        continue
                    row = await database.voice_get_or_create(member.id, guild.id)
                    if row["promoted"]:
                        continue
                    if not row["session_start"]:
                        continue
                    elapsed_now = row["total_seconds"] + max(0, now - row["session_start"])
                    if elapsed_now // (config.VOICE_ACTIVITY_THRESHOLD_MINUTES * 60) > row["proposal_count"]:
                        await self._maybe_propose(member, elapsed_now)

    @check_active_sessions.before_loop
    async def before_check(self):
        await self.bot.wait_until_ready()


async def setup(bot: commands.Bot):
    await bot.add_cog(Affinity(bot))