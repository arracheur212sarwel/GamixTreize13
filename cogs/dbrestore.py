"""
cogs/dbrestore.py
Commande TEMPORAIRE réservée au propriétaire du bot, pour transférer la
base SQLite locale (data/bot.db) vers le volume Railway en une seule fois.

À SUPPRIMER (retirer ce fichier du dossier cogs/) une fois la migration
terminée, pour ne pas laisser une commande aussi sensible active en
permanence.
"""

import os

import discord
from discord import app_commands
from discord.ext import commands

import database


class DBRestore(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="restore-db", description="[Propriétaire uniquement] Remplace la base de données par un fichier .db envoyé.")
    @app_commands.describe(fichier="Le fichier bot.db à restaurer")
    async def restore_db(self, interaction: discord.Interaction, fichier: discord.Attachment):
        if not await self.bot.is_owner(interaction.user):
            return await interaction.response.send_message("❌ Réservé au propriétaire du bot.", ephemeral=True)

        if not fichier.filename.endswith(".db"):
            return await interaction.response.send_message("❌ Le fichier doit avoir l'extension .db", ephemeral=True)

        await interaction.response.defer(ephemeral=True)

        await database.close_db()

        os.makedirs("data", exist_ok=True)
        db_path = database.DB_PATH
        for suffix in ("", "-wal", "-shm"):
            path = db_path + suffix
            if os.path.exists(path):
                os.remove(path)

        content = await fichier.read()
        with open(db_path, "wb") as f:
            f.write(content)

        await database.init_db()

        await interaction.followup.send(
            "✅ Base de données restaurée avec succès. Pense à retirer `cogs/dbrestore.py` maintenant."
        )


async def setup(bot: commands.Bot):
    await bot.add_cog(DBRestore(bot))