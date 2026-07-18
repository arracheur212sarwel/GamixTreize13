"""
utils/permissions.py
Portage Python de TicketGMT/src/utils/permissions.js
"""

import discord

import config


def is_staff(member: discord.Member) -> bool:
    if member is None:
        return False
    if member.guild_permissions.manage_channels:
        return True
    if config.TICKET_STAFF_ROLE and any(r.id == config.TICKET_STAFF_ROLE for r in member.roles):
        return True
    return False


def is_admin(member: discord.Member) -> bool:
    return bool(member) and member.guild_permissions.administrator
