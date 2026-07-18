"""
cogs/smashorpass.py
Module "Smash or Pass" : surveille config.SOP_CHANNEL_ID, crée automatiquement
un thread + embed de vote pour chaque photo postée, fournit /top et ferme
automatiquement les votes expirés.
"""

from datetime import datetime, timedelta, timezone

import discord
from discord import app_commands
from discord.ext import commands, tasks

import config
import database
from embeds.vote_embed import build_vote_embed
from views.vote_view import VoteView

MEDALS = ["🥇", "🥈", "🥉"]


class SmashOrPass(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        if config.SOP_CHANNEL_ID:
            self.check_expired_posts.change_interval(minutes=config.SOP_CHECK_INTERVAL_MINUTES)
            self.check_expired_posts.start()

    def cog_unload(self):
        self.check_expired_posts.cancel()


    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot:
            return
        if not config.SOP_CHANNEL_ID or message.channel.id != config.SOP_CHANNEL_ID:
            return

        image_attachments = [
            a for a in message.attachments if a.content_type and a.content_type.startswith("image/")
        ]
        if not image_attachments:
            return

        await self._create_vote_post(message)

    async def _create_vote_post(self, message: discord.Message):
        now = datetime.now(timezone.utc)
        end_at = now + timedelta(hours=config.SOP_VOTE_DURATION_HOURS)

        thread = await message.create_thread(
            name=f"📸 {message.author.display_name}"[:100],
            auto_archive_duration=4320,
        )

        embed = build_vote_embed(0, 0, end_at)
        view = VoteView(message.id)

        embed_message = await thread.send(embed=embed, view=view)

        await database.sop_create_post(
            message_id=message.id,
            thread_id=thread.id,
            embed_message_id=embed_message.id,
            guild_id=message.guild.id,
            channel_id=message.channel.id,
            author_id=message.author.id,
            author_name=message.author.display_name,
            created_at=now.isoformat(),
            end_at=end_at.isoformat(),
        )


    @app_commands.command(name="topsop", description="Affiche les 10 publications avec le plus de Smash")
    async def top(self, interaction: discord.Interaction):
        posts = await database.sop_get_top_posts(limit=10)

        if not posts:
            await interaction.response.send_message("Aucune publication pour le moment.", ephemeral=True)
            return

        embed = discord.Embed(title="🏆 Top Smash or Pass", color=discord.Color.gold())
        lines = []
        for i, post in enumerate(posts):
            rank_icon = MEDALS[i] if i < len(MEDALS) else f"**{i + 1}.**"
            link = f"https://discord.com/channels/{post['guild_id']}/{post['channel_id']}/{post['message_id']}"
            lines.append(f"{rank_icon} [{post['author_name']}]({link}) — {post['smash_count']} ❤️")
        embed.description = "\n".join(lines)
        await interaction.response.send_message(embed=embed)


    @tasks.loop(minutes=5)
    async def check_expired_posts(self):
        now_iso = datetime.now(timezone.utc).isoformat()
        expired = await database.sop_get_expired_posts(now_iso)
        for post in expired:
            try:
                await self._close_post(post)
            except Exception:
                self.bot.logger.exception("Erreur lors de la fermeture de la publication %s", post["message_id"])

    @check_expired_posts.before_loop
    async def before_check(self):
        await self.bot.wait_until_ready()

    async def _close_post(self, post: dict):
        thread = self.bot.get_channel(post["thread_id"])
        if thread is None:
            try:
                thread = await self.bot.fetch_channel(post["thread_id"])
            except (discord.NotFound, discord.Forbidden, discord.HTTPException):
                thread = None

        counts = await database.sop_get_vote_counts(post["message_id"])
        end_at = datetime.fromisoformat(post["end_at"])
        embed = build_vote_embed(counts["smash"], counts["pass"], end_at, closed=True)
        view = VoteView(post["message_id"], disabled=True)

        if thread is not None:
            try:
                embed_message = await thread.fetch_message(post["embed_message_id"])
                await embed_message.edit(embed=embed, view=view)
            except (discord.NotFound, discord.Forbidden, discord.HTTPException):
                pass

            if isinstance(thread, discord.Thread):
                try:
                    await thread.edit(locked=True, archived=True)
                except (discord.Forbidden, discord.HTTPException):
                    pass

        await database.sop_close_post(post["message_id"])


async def setup(bot: commands.Bot):
    await bot.add_cog(SmashOrPass(bot))