import discord
from discord.ext import commands
from discord import app_commands

from config import COLOR_SUCCESS, COLOR_ERROR
from database import get_db


class AdminConfig(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    config_group = app_commands.Group(name="config", description="Configuration du bot")

    @config_group.command(name="logs", description="Définir le salon des logs")
    @app_commands.default_permissions(administrator=True)
    async def set_logs(self, interaction: discord.Interaction, salon: discord.TextChannel):
        db = await get_db()
        await db.execute(
            "INSERT INTO guild_config (guild_id, logs_channel) VALUES (?, ?) "
            "ON CONFLICT(guild_id) DO UPDATE SET logs_channel = excluded.logs_channel",
            (interaction.guild.id, salon.id),
        )
        await db.commit()
        embed = discord.Embed(description=f"✅ Salon des logs défini sur {salon.mention}", color=COLOR_SUCCESS)
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @config_group.command(name="staff_role", description="Définir le rôle staff")
    @app_commands.default_permissions(administrator=True)
    async def set_staff_role(self, interaction: discord.Interaction, role: discord.Role):
        db = await get_db()
        await db.execute(
            "INSERT INTO guild_config (guild_id, staff_role) VALUES (?, ?) "
            "ON CONFLICT(guild_id) DO UPDATE SET staff_role = excluded.staff_role",
            (interaction.guild.id, role.id),
        )
        await db.commit()
        await interaction.response.send_message(
            embed=discord.Embed(description=f"Rôle staff défini sur {role.mention}", color=COLOR_SUCCESS),
            ephemeral=True,
        )

    @config_group.command(name="mute_role", description="Définir le rôle mute")
    @app_commands.default_permissions(administrator=True)
    async def set_mute_role(self, interaction: discord.Interaction, role: discord.Role):
        db = await get_db()
        await db.execute(
            "INSERT INTO guild_config (guild_id, mute_role) VALUES (?, ?) "
            "ON CONFLICT(guild_id) DO UPDATE SET mute_role = excluded.mute_role",
            (interaction.guild.id, role.id),
        )
        await db.commit()
        await interaction.response.send_message(
            embed=discord.Embed(description=f"Rôle mute défini sur {role.mention}", color=COLOR_SUCCESS),
            ephemeral=True,
        )

    @config_group.command(name="color", description="Changer la couleur des embeds (ex: #FF0000)")
    @app_commands.default_permissions(administrator=True)
    async def set_color(self, interaction: discord.Interaction, couleur: str):
        try:
            int(couleur.strip("#"), 16)
        except ValueError:
            return await interaction.response.send_message(
                embed=discord.Embed(description="Couleur invalide. Format hexadécimal attendu.", color=COLOR_ERROR),
                ephemeral=True,
            )
        db = await get_db()
        await db.execute(
            "INSERT INTO guild_config (guild_id, embed_color) VALUES (?, ?) "
            "ON CONFLICT(guild_id) DO UPDATE SET embed_color = excluded.embed_color",
            (interaction.guild.id, couleur),
        )
        await db.commit()
        await interaction.response.send_message(
            embed=discord.Embed(description=f"Couleur définie sur `{couleur}`", color=COLOR_SUCCESS),
            ephemeral=True,
        )

    @config_group.command(name="language", description="Changer la langue (fr/en)")
    @app_commands.default_permissions(administrator=True)
    async def set_language(self, interaction: discord.Interaction, langue: str):
        if langue not in ("fr", "en"):
            return await interaction.response.send_message(
                embed=discord.Embed(description="Langues disponibles : fr, en", color=COLOR_ERROR),
                ephemeral=True,
            )
        db = await get_db()
        await db.execute(
            "INSERT INTO guild_config (guild_id, language) VALUES (?, ?) "
            "ON CONFLICT(guild_id) DO UPDATE SET language = excluded.language",
            (interaction.guild.id, langue),
        )
        await db.commit()
        await interaction.response.send_message(
            embed=discord.Embed(description=f"Langue définie sur `{langue}`", color=COLOR_SUCCESS),
            ephemeral=True,
        )


async def setup(bot: commands.Bot):
    await bot.add_cog(AdminConfig(bot))
