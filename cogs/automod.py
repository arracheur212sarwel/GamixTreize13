import discord
from discord.ext import commands
import datetime
import asyncio
import re
from config import COLOR_WARNING
import config

class AutoMod(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.spam_cache = {}

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot or not message.guild:
            return
        await self.check_spam(message)
        await self.check_mentions(message)
        await self.check_photos(message)

    async def check_spam(self, message: discord.Message):
        now = datetime.datetime.utcnow()
        user_id = message.author.id
        if user_id not in self.spam_cache:
            self.spam_cache[user_id] = []
        self.spam_cache[user_id].append(now)
        self.spam_cache[user_id] = [t for t in self.spam_cache[user_id] if (now - t).total_seconds() <= 5]
        if len(self.spam_cache[user_id]) >= 5:
            try:
                until = discord.utils.utcnow() + datetime.timedelta(minutes=5)
                await message.author.timeout(until, reason="AutoMod: spam")
                await message.channel.send(f"{message.author.mention} a été timeout pour spam.", delete_after=10)
            except:
                pass
            self.spam_cache[user_id] = []

    async def check_links(self, message: discord.Message):
        if re.search(r'https?://', message.content):
            if not message.author.guild_permissions.manage_messages:
                try:
                    await message.delete()
                    await message.channel.send(f"{message.author.mention}, les liens ne sont pas autorisés.", delete_after=5)
                except:
                    pass

    async def check_mentions(self, message: discord.Message):
        if message.mention_everyone or len(message.mentions) >= 20:
            if not message.author.guild_permissions.manage_messages:
                try:
                    await message.delete()
                    await message.channel.send(f"{message.author.mention}, le spam de mentions est interdit.", delete_after=5)
                except:
                    pass

    async def check_photos(self, message: discord.Message):
        allowed_channels = {c for c in (config.MEDIA_CHANNEL_ID, config.SOP_CHANNEL_ID) if c}
        if not allowed_channels or message.channel.id in allowed_channels:
            return
        has_photo = any(
            a.content_type and a.content_type.startswith("image/") for a in message.attachments
        )
        if not has_photo:
            return
        if message.author.guild_permissions.manage_messages:
            return
        try:
            await message.delete()
            media_channel = message.guild.get_channel(config.MEDIA_CHANNEL_ID) if config.MEDIA_CHANNEL_ID else None
            hint = f" (utilise {media_channel.mention})" if media_channel else ""
            await message.channel.send(
                f"{message.author.mention}, les photos ne sont autorisées que dans le salon media{hint}.",
                delete_after=5,
            )
        except:
            pass

async def setup(bot: commands.Bot):
    await bot.add_cog(AutoMod(bot))
