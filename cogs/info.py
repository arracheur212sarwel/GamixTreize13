import discord
from discord.ext import commands
from discord import app_commands
from config import COLOR_SUCCESS

class Info(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="userinfo", description="Informations sur un utilisateur")
    async def userinfo(self, interaction: discord.Interaction, membre: discord.Member = None):
        if membre is None:
            membre = interaction.user
        embed = discord.Embed(title=f"Informations sur {membre.display_name}", color=membre.color or COLOR_SUCCESS)
        embed.set_thumbnail(url=membre.display_avatar.url)
        embed.add_field(name="ID", value=membre.id)
        embed.add_field(name="Compte créé le", value=membre.created_at.strftime("%d/%m/%Y %H:%M"))
        embed.add_field(name="A rejoint le", value=membre.joined_at.strftime("%d/%m/%Y %H:%M") if membre.joined_at else "Inconnu")
        embed.add_field(name="Rôles", value=", ".join([r.mention for r in membre.roles if r != interaction.guild.default_role]) or "Aucun", inline=False)
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="serverinfo", description="Informations sur le serveur")
    async def serverinfo(self, interaction: discord.Interaction):
        guild = interaction.guild
        embed = discord.Embed(title=f"Informations sur {guild.name}", color=COLOR_SUCCESS)
        embed.set_thumbnail(url=guild.icon.url if guild.icon else None)
        embed.add_field(name="Propriétaire", value=guild.owner.mention)
        embed.add_field(name="Membres", value=guild.member_count)
        embed.add_field(name="Boosts", value=guild.premium_subscription_count)
        embed.add_field(name="Salons", value=len(guild.channels))
        embed.add_field(name="Rôles", value=len(guild.roles))
        embed.add_field(name="Créé le", value=guild.created_at.strftime("%d/%m/%Y"))
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="avatar", description="Afficher l'avatar d'un utilisateur")
    async def avatar(self, interaction: discord.Interaction, membre: discord.Member = None):
        if membre is None:
            membre = interaction.user
        embed = discord.Embed(title=f"Avatar de {membre.display_name}", color=COLOR_SUCCESS)
        embed.set_image(url=membre.display_avatar.url)
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="roleinfo", description="Informations sur un rôle")
    async def roleinfo(self, interaction: discord.Interaction, role: discord.Role):
        embed = discord.Embed(title=f"Rôle : {role.name}", color=role.color or COLOR_SUCCESS)
        embed.add_field(name="ID", value=role.id)
        embed.add_field(name="Couleur", value=str(role.color))
        embed.add_field(name="Mentionnable", value=role.mentionable)
        embed.add_field(name="Affiché séparément", value=role.hoist)
        embed.add_field(name="Position", value=role.position)
        embed.add_field(name="Permissions", value=", ".join([perm for perm, value in role.permissions if value])[:1024] or "Aucune", inline=False)
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="channelinfo", description="Informations sur un salon")
    async def channelinfo(self, interaction: discord.Interaction, salon: discord.TextChannel = None):
        if salon is None:
            salon = interaction.channel
        embed = discord.Embed(title=f"Salon : {salon.name}", color=COLOR_SUCCESS)
        embed.add_field(name="ID", value=salon.id)
        embed.add_field(name="Type", value=str(salon.type))
        embed.add_field(name="Catégorie", value=salon.category.name if salon.category else "Aucune")
        embed.add_field(name="Sujet", value=salon.topic or "Aucun")
        embed.add_field(name="Mode lent", value=f"{salon.slowmode_delay}s")
        embed.add_field(name="NSFW", value=salon.is_nsfw())
        await interaction.response.send_message(embed=embed)

async def setup(bot: commands.Bot):
    await bot.add_cog(Info(bot))