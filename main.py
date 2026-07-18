"""
main.py
Point d'entrée du bot Discord unifié : Modération + AutoMod/Info/Logs
(ex-GamixTreize13) + Smash or Pass (ex-SmashOrPassBot) + Tickets
(ex-TicketGMT, porté de Node.js vers Python).

Un seul process, un seul token, une seule base SQLite (data/bot.db).
"""

import logging
import os

import discord
from discord.ext import commands

import config
import database
from views.vote_view import VoteView
from views.ticket_views import TicketPanelView, TicketOpenView, TicketClosedView

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("bot")


class UnifiedBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True
        intents.members = True
        intents.guilds = True
        intents.messages = True
        super().__init__(command_prefix="!", intents=intents)
        self.logger = logger

    async def setup_hook(self):
        await database.init_db()
        logger.info("Base de données connectée.")

        for filename in os.listdir("./cogs"):
            if filename.endswith(".py") and filename != "__init__.py":
                await self.load_extension(f"cogs.{filename[:-3]}")
                logger.info("Cog chargé : %s", filename)

        self.add_view(TicketPanelView())
        self.add_view(TicketOpenView())
        self.add_view(TicketClosedView())

        active_posts = await database.sop_get_active_posts()
        for post in active_posts:
            self.add_view(VoteView(post["message_id"], disabled=post["closed"]))
        logger.info("%d vue(s) Smash or Pass réenregistrée(s).", len(active_posts))

        if config.GUILD_ID:
            guild = discord.Object(id=config.GUILD_ID)
            self.tree.copy_global_to(guild=guild)
            await self.tree.sync(guild=guild)
            logger.info("Commandes slash synchronisées sur la guilde %s.", config.GUILD_ID)
        else:
            await self.tree.sync()
            logger.info("Commandes slash synchronisées globalement (peut prendre jusqu'à 1h à se propager).")

    async def on_ready(self):
        logger.info("Connecté en tant que %s (ID: %s)", self.user, self.user.id)
        activity = discord.CustomActivity(name="Pas dpermis")
        await self.change_presence(activity=activity)

    async def close(self):
        await database.close_db()
        await super().close()


bot = UnifiedBot()

if __name__ == "__main__":
    bot.run(config.TOKEN)