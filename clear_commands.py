"""
clear_commands.py
Script à lancer UNE SEULE FOIS pour supprimer toutes les commandes slash
existantes (globales ET sur la guilde), avant de relancer main.py qui les
réenregistrera proprement à un seul endroit.

Usage : py clear_commands.py
"""

import asyncio

import discord
from discord.ext import commands

import config

intents = discord.Intents.default()


class CleanupBot(commands.Bot):
    async def setup_hook(self):
        self.tree.clear_commands(guild=None)
        await self.tree.sync()
        print("Commandes globales supprimées.")

        if config.GUILD_ID:
            guild = discord.Object(id=config.GUILD_ID)
            self.tree.clear_commands(guild=guild)
            await self.tree.sync(guild=guild)
            print(f"Commandes de la guilde {config.GUILD_ID} supprimées.")

        print("Nettoyage terminé. Relance main.py pour resynchroniser proprement.")
        await self.close()


bot = CleanupBot(command_prefix="!", intents=intents)

if __name__ == "__main__":
    asyncio.run(bot.start(config.TOKEN))
