import discord
from discord.ext import commands
from discord import app_commands
from datetime import timedelta, datetime
import asyncio
from config import COLOR_SUCCESS, COLOR_WARNING, COLOR_ERROR, TIMEOUT_DURATIONS
from database import get_db

class UnwarnSelect(discord.ui.Select):
    def __init__(self, warns):
        options = [
            discord.SelectOption(
                label=f"#{w['id']} - {(w['reason'] or 'Aucune raison')[:80]}",
                value=str(w["id"]),
                description=f"Le {w['date']}"[:100],
            )
            for w in warns
        ]
        super().__init__(placeholder="Choisis l'avertissement à supprimer...", options=options)

    async def callback(self, interaction: discord.Interaction):
        warn_id = int(self.values[0])
        db = await get_db()
        await db.execute("DELETE FROM warns WHERE id = ?", (warn_id,))
        await db.commit()
        embed = discord.Embed(title="✅ Avertissement supprimé", description=f"Warn `#{warn_id}` retiré.", color=COLOR_SUCCESS)
        await interaction.response.edit_message(embed=embed, view=None)


class UnwarnView(discord.ui.View):
    def __init__(self, warns):
        super().__init__(timeout=60)
        self.add_item(UnwarnSelect(warns))


class Moderation(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    async def check_hierarchy(self, interaction: discord.Interaction, target: discord.Member, action: str):
        if target == interaction.guild.owner:
            raise commands.BadArgument(f"Vous ne pouvez pas {action} le propriétaire du serveur.")
        if target.top_role >= interaction.user.top_role and interaction.user != interaction.guild.owner:
            raise commands.BadArgument(f"Vous ne pouvez pas {action} un membre ayant un rôle supérieur ou égal au vôtre.")
        if target == self.bot.user:
            raise commands.BadArgument(f"Je ne peux pas me {action} moi-même.")
        return True

    async def log_mod_action(self, guild: discord.Guild, embed: discord.Embed):
        db = await get_db()
        cursor = await db.execute("SELECT logs_channel FROM guild_config WHERE guild_id = ?", (guild.id,))
        row = await cursor.fetchone()
        if row and row["logs_channel"]:
            channel = guild.get_channel(row["logs_channel"])
            if channel:
                await channel.send(embed=embed)

    @app_commands.command(name="ban", description="Bannir un membre")
    @app_commands.default_permissions(ban_members=True)
    async def ban(self, interaction: discord.Interaction, membre: discord.Member, raison: str, dm: bool = False):
        await interaction.response.defer(ephemeral=False)
        await asyncio.sleep(0)
        await self.check_hierarchy(interaction, membre, "ban")
        if dm:
            try:
                embed_dm = discord.Embed(title="Vous avez été banni", description=f"**Serveur :** {interaction.guild.name}\n**Raison :** {raison}", color=COLOR_ERROR)
                await membre.send(embed=embed_dm)
            except:
                pass
        await membre.ban(reason=raison)
        db = await get_db()
        await db.execute("INSERT INTO punishments (type, user_id, guild_id, moderator_id, reason) VALUES (?, ?, ?, ?, ?)",
                         ("ban", membre.id, interaction.guild.id, interaction.user.id, raison))
        await db.commit()
        embed = discord.Embed(title="🔨 Ban", color=COLOR_SUCCESS)
        embed.add_field(name="Utilisateur", value=f"{membre.mention} ({membre.id})", inline=False)
        embed.add_field(name="Modérateur", value=interaction.user.mention, inline=False)
        embed.add_field(name="Raison", value=raison, inline=False)
        embed.timestamp = discord.utils.utcnow()
        await interaction.followup.send(embed=embed, ephemeral=False)
        await self.log_mod_action(interaction.guild, embed)

    @app_commands.command(name="unban", description="Débannir un utilisateur")
    @app_commands.default_permissions(ban_members=True)
    async def unban(self, interaction: discord.Interaction, identifiant: str, raison: str):
        await interaction.response.defer(ephemeral=False)
        await asyncio.sleep(0)
        try:
            user = await self.bot.fetch_user(int(identifiant))
        except:
            return await interaction.followup.send(embed=discord.Embed(description="ID invalide.", color=COLOR_ERROR), ephemeral=True)
        await interaction.guild.unban(user, reason=raison)
        embed = discord.Embed(title="🔓 Unban", description=f"{user.mention} a été débanni.", color=COLOR_SUCCESS)
        embed.add_field(name="Raison", value=raison, inline=False)
        embed.add_field(name="Modérateur", value=interaction.user.mention, inline=False)
        embed.timestamp = discord.utils.utcnow()
        await interaction.followup.send(embed=embed, ephemeral=False)

    @app_commands.command(name="kick", description="Expulser un membre")
    @app_commands.default_permissions(kick_members=True)
    async def kick(self, interaction: discord.Interaction, membre: discord.Member, raison: str):
        await interaction.response.defer(ephemeral=False)
        await asyncio.sleep(0)
        await self.check_hierarchy(interaction, membre, "expulser")
        await membre.kick(reason=raison)
        db = await get_db()
        await db.execute("INSERT INTO punishments (type, user_id, guild_id, moderator_id, reason) VALUES (?, ?, ?, ?, ?)",
                         ("kick", membre.id, interaction.guild.id, interaction.user.id, raison))
        await db.commit()
        embed = discord.Embed(title="👢 Kick", color=COLOR_SUCCESS)
        embed.add_field(name="Utilisateur", value=f"{membre.mention} ({membre.id})", inline=False)
        embed.add_field(name="Modérateur", value=interaction.user.mention, inline=False)
        embed.add_field(name="Raison", value=raison, inline=False)
        embed.timestamp = discord.utils.utcnow()
        await interaction.followup.send(embed=embed, ephemeral=False)
        await self.log_mod_action(interaction.guild, embed)

    @app_commands.command(name="timeout", description="Mettre un membre en silence temporaire")
    @app_commands.default_permissions(moderate_members=True)
    async def timeout(self, interaction: discord.Interaction, membre: discord.Member, duree: str, raison: str):
        await interaction.response.defer(ephemeral=False)
        await asyncio.sleep(0)
        await self.check_hierarchy(interaction, membre, "timeout")
        if duree not in TIMEOUT_DURATIONS:
            valid = ", ".join(TIMEOUT_DURATIONS.keys())
            return await interaction.followup.send(embed=discord.Embed(description=f"Durée invalide. Valeurs acceptées : {valid}", color=COLOR_ERROR), ephemeral=True)
        seconds = TIMEOUT_DURATIONS[duree]
        until = discord.utils.utcnow() + timedelta(seconds=seconds)
        await membre.timeout(until, reason=raison)
        db = await get_db()
        await db.execute("INSERT INTO punishments (type, user_id, guild_id, moderator_id, reason, duration) VALUES (?, ?, ?, ?, ?, ?)",
                         ("timeout", membre.id, interaction.guild.id, interaction.user.id, raison, seconds))
        await db.commit()
        embed = discord.Embed(title="⏱️ Timeout", color=COLOR_SUCCESS)
        embed.add_field(name="Utilisateur", value=membre.mention, inline=False)
        embed.add_field(name="Durée", value=duree, inline=False)
        embed.add_field(name="Raison", value=raison, inline=False)
        embed.add_field(name="Modérateur", value=interaction.user.mention, inline=False)
        embed.timestamp = discord.utils.utcnow()
        await interaction.followup.send(embed=embed, ephemeral=False)
        await self.log_mod_action(interaction.guild, embed)

    @app_commands.command(name="untimeout", description="Retirer le timeout d'un membre")
    @app_commands.default_permissions(moderate_members=True)
    async def untimeout(self, interaction: discord.Interaction, membre: discord.Member, raison: str):
        await interaction.response.defer(ephemeral=False)
        await asyncio.sleep(0)
        await self.check_hierarchy(interaction, membre, "untimeout")
        await membre.timeout(None, reason=raison)
        embed = discord.Embed(title="✅ Timeout retiré", description=f"Timeout de {membre.mention} retiré.", color=COLOR_SUCCESS)
        await interaction.followup.send(embed=embed, ephemeral=False)

    @app_commands.command(name="warn", description="Avertir un membre")
    @app_commands.default_permissions(moderate_members=True)
    async def warn(self, interaction: discord.Interaction, membre: discord.Member, raison: str):
        await interaction.response.defer(ephemeral=False)
        await asyncio.sleep(0)
        await self.check_hierarchy(interaction, membre, "avertir")
        db = await get_db()
        await db.execute("INSERT INTO warns (user_id, guild_id, moderator_id, reason) VALUES (?, ?, ?, ?)",
                         (membre.id, interaction.guild.id, interaction.user.id, raison))
        await db.commit()
        embed = discord.Embed(title="⚠️ Avertissement", color=COLOR_WARNING)
        embed.add_field(name="Utilisateur", value=membre.mention, inline=False)
        embed.add_field(name="Raison", value=raison, inline=False)
        embed.add_field(name="Modérateur", value=interaction.user.mention, inline=False)
        embed.timestamp = discord.utils.utcnow()
        await interaction.followup.send(embed=embed, ephemeral=False)
        await self.log_mod_action(interaction.guild, embed)

    @app_commands.command(name="unwarn", description="Supprimer un avertissement d'un membre")
    @app_commands.default_permissions(moderate_members=True)
    async def unwarn(self, interaction: discord.Interaction, membre: discord.Member):
        await interaction.response.defer(ephemeral=True)
        db = await get_db()
        cursor = await db.execute(
            "SELECT * FROM warns WHERE user_id = ? AND guild_id = ? ORDER BY date DESC",
            (membre.id, interaction.guild.id),
        )
        rows = await cursor.fetchall()
        if not rows:
            return await interaction.followup.send(
                embed=discord.Embed(description=f"{membre.mention} n'a aucun avertissement.", color=COLOR_ERROR),
                ephemeral=True,
            )
        warns = [dict(r) for r in rows][:25]
        embed = discord.Embed(
            title=f"Avertissements de {membre.display_name}",
            description="Sélectionne l'avertissement à supprimer dans le menu ci-dessous.",
            color=COLOR_WARNING,
        )
        await interaction.followup.send(embed=embed, view=UnwarnView(warns), ephemeral=True)

    @app_commands.command(name="history", description="Historique des sanctions d'un membre")
    @app_commands.default_permissions(moderate_members=True)
    async def history(self, interaction: discord.Interaction, membre: discord.Member):
        await interaction.response.defer(ephemeral=False)
        await asyncio.sleep(0)
        db = await get_db()
        warns = await db.execute_fetchall("SELECT * FROM warns WHERE user_id = ? AND guild_id = ? ORDER BY date DESC", (membre.id, interaction.guild.id))
        puns = await db.execute_fetchall("SELECT * FROM punishments WHERE user_id = ? AND guild_id = ? ORDER BY date DESC", (membre.id, interaction.guild.id))
        embed = discord.Embed(title=f"Historique de {membre.display_name}", color=COLOR_WARNING)
        if warns:
            warn_text = "\n".join([f"**#{w[0]}** : {w[4]} (par <@{w[3]}> le {w[5]})" for w in warns])
            embed.add_field(name="⚠️ Warnings", value=warn_text, inline=False)
        if puns:
            pun_text = "\n".join([f"**{p[1]}** : {p[5]} (durée: {p[6] if p[6] else 'N/A'}, par <@{p[4]}> le {p[7]})" for p in puns])
            embed.add_field(name="🔨 Sanctions", value=pun_text, inline=False)
        if not warns and not puns:
            embed.description = "Aucun antécédent."
        await interaction.followup.send(embed=embed, ephemeral=False)

    @app_commands.command(name="clear", description="Supprimer des messages")
    @app_commands.default_permissions(manage_messages=True)
    async def clear(self, interaction: discord.Interaction, nombre: int = 1):
        await interaction.response.defer(ephemeral=True)
        await asyncio.sleep(0)
        if nombre > 100:
            return await interaction.followup.send(embed=discord.Embed(description="Maximum 100 messages.", color=COLOR_ERROR), ephemeral=True)
        deleted = await interaction.channel.purge(limit=nombre)
        embed = discord.Embed(description=f"✅ {len(deleted)} message(s) supprimé(s).", color=COLOR_SUCCESS)
        await interaction.followup.send(embed=embed, ephemeral=True)

    @app_commands.command(name="slowmode", description="Définir le mode lent du salon")
    @app_commands.default_permissions(manage_channels=True)
    async def slowmode(self, interaction: discord.Interaction, secondes: int = 0):
        await interaction.response.defer(ephemeral=False)
        await asyncio.sleep(0)
        await interaction.channel.edit(slowmode_delay=secondes)
        if secondes == 0:
            await interaction.followup.send(embed=discord.Embed(description="Mode lent désactivé.", color=COLOR_SUCCESS))
        else:
            await interaction.followup.send(embed=discord.Embed(description=f"Mode lent défini à {secondes} seconde(s).", color=COLOR_SUCCESS))

    @app_commands.command(name="lock", description="Verrouiller le salon")
    @app_commands.default_permissions(manage_channels=True)
    async def lock(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=False)
        await asyncio.sleep(0)
        overwrite = interaction.channel.overwrites_for(interaction.guild.default_role)
        overwrite.send_messages = False
        await interaction.channel.set_permissions(interaction.guild.default_role, overwrite=overwrite)
        await interaction.followup.send(embed=discord.Embed(description="🔒 Salon verrouillé.", color=COLOR_SUCCESS))

    @app_commands.command(name="unlock", description="Déverrouiller le salon")
    @app_commands.default_permissions(manage_channels=True)
    async def unlock(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=False)
        await asyncio.sleep(0)
        overwrite = interaction.channel.overwrites_for(interaction.guild.default_role)
        overwrite.send_messages = None
        await interaction.channel.set_permissions(interaction.guild.default_role, overwrite=overwrite)
        await interaction.followup.send(embed=discord.Embed(description="🔓 Salon déverrouillé.", color=COLOR_SUCCESS))

    @app_commands.command(name="nick", description="Changer le pseudonyme d'un membre")
    @app_commands.default_permissions(manage_nicknames=True)
    async def nick(self, interaction: discord.Interaction, membre: discord.Member, pseudo: str):
        await interaction.response.defer(ephemeral=False)
        await asyncio.sleep(0)
        await self.check_hierarchy(interaction, membre, "renommer")
        await membre.edit(nick=pseudo)
        embed = discord.Embed(description=f"Pseudo de {membre.mention} changé en **{pseudo}**.", color=COLOR_SUCCESS)
        await interaction.followup.send(embed=embed)

async def setup(bot: commands.Bot):
    await bot.add_cog(Moderation(bot))