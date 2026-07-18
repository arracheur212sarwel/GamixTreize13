import discord

import config
import database


class AffinityProposalView(discord.ui.View):
    def __init__(self, target_id: int):
        super().__init__(timeout=None)
        self.target_id = target_id
        self.validate_button.custom_id = f"affinity:validate:{target_id}"
        self.refuse_button.custom_id = f"affinity:refuse:{target_id}"

    def _is_staff(self, member: discord.Member) -> bool:
        if member.guild_permissions.manage_roles:
            return True
        if config.TICKET_STAFF_ROLE and any(r.id == config.TICKET_STAFF_ROLE for r in member.roles):
            return True
        return False

    @discord.ui.button(label="Valider", emoji="✅", style=discord.ButtonStyle.success, custom_id="affinity:validate:placeholder")
    async def validate_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not self._is_staff(interaction.user):
            return await interaction.response.send_message("Seuls les modérateurs peuvent valider.", ephemeral=True)

        guild = interaction.guild
        target = guild.get_member(self.target_id)
        if not target:
            return await interaction.response.edit_message(
                content="❌ Ce membre a quitté le serveur.", embed=None, view=None
            )

        old_role = guild.get_role(config.WELCOME_ROLE_ID) if config.WELCOME_ROLE_ID else None
        new_role = guild.get_role(config.ACTIVE_ROLE_ID) if config.ACTIVE_ROLE_ID else None

        try:
            if old_role and old_role in target.roles:
                await target.remove_roles(old_role, reason=f"Passage au rôle actif validé par {interaction.user}")
            if new_role:
                await target.add_roles(new_role, reason=f"Passage au rôle actif validé par {interaction.user}")
        except discord.HTTPException:
            return await interaction.response.send_message("❌ Erreur lors du changement de rôle (permissions du bot ?).", ephemeral=True)

        await database.voice_mark_promoted(self.target_id, guild.id)

        for item in self.children:
            item.disabled = True
        await interaction.response.edit_message(
            content=f"✅ {target.mention} est passé au rôle actif (validé par {interaction.user.mention}).",
            embed=None, view=self,
        )

    @discord.ui.button(label="Refuser", emoji="❌", style=discord.ButtonStyle.danger, custom_id="affinity:refuse:placeholder")
    async def refuse_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not self._is_staff(interaction.user):
            return await interaction.response.send_message("Seuls les modérateurs peuvent refuser.", ephemeral=True)

        for item in self.children:
            item.disabled = True
        await interaction.response.edit_message(
            content=f"❌ Proposition refusée par {interaction.user.mention}.", embed=None, view=self
        )