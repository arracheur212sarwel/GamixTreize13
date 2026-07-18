"""
utils/ticket_logger.py
Portage Python de TicketGMT/src/utils/logger.js
"""

import logging

import discord

import config
from embeds.ticket_embed import base_embed, log_embed

_log = logging.getLogger("bot.tickets")


async def log_ticket_event(client: discord.Client, action: str, user: discord.abc.User, ticket_channel_id: int, extra: str = None):
    if not config.TICKET_LOGS_CHANNEL:
        return
    try:
        logs_channel = client.get_channel(config.TICKET_LOGS_CHANNEL) or await client.fetch_channel(config.TICKET_LOGS_CHANNEL)
    except (discord.NotFound, discord.Forbidden, discord.HTTPException):
        _log.warning("Salon de logs introuvable (vérifie TICKET_LOGS_CHANNEL dans .env).")
        return
    embed = log_embed(action, user, ticket_channel_id, extra)
    try:
        await logs_channel.send(embed=embed)
    except discord.HTTPException as exc:
        _log.error("Échec de l'envoi du log: %s", exc)


async def log_action(client: discord.Client, title: str, description: str):
    if not config.TICKET_LOGS_CHANNEL:
        return
    try:
        logs_channel = client.get_channel(config.TICKET_LOGS_CHANNEL) or await client.fetch_channel(config.TICKET_LOGS_CHANNEL)
    except (discord.NotFound, discord.Forbidden, discord.HTTPException):
        return
    embed = base_embed()
    embed.title = title
    embed.description = description
    embed.color = 0xFEE75C
    try:
        await logs_channel.send(embed=embed)
    except discord.HTTPException as exc:
        _log.error("Échec logAction: %s", exc)
