"""
utils/transcript.py
Génère un transcript HTML simple d'un salon de ticket (équivalent Python de
la librairie discord-html-transcripts utilisée par TicketGMT en JS), puis
l'envoie dans le salon de logs et/ou en DM au créateur du ticket.
"""

import html
import io
import logging

import discord

import config
from utils.ticket_logger import log_action

_log = logging.getLogger("bot.tickets")

_HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="fr">
<head>
<meta charset="utf-8">
<title>Transcript - {channel_name}</title>
<style>
  body {{ background:#313338; color:#dbdee1; font-family: "gg sans", "Helvetica Neue", Arial, sans-serif; margin:0; padding:20px; }}
  h1 {{ color:#fff; }}
  .msg {{ display:flex; gap:12px; padding:8px 0; border-bottom:1px solid #3f4147; }}
  .avatar {{ width:40px; height:40px; border-radius:50%; flex-shrink:0; }}
  .meta {{ font-size:0.85em; color:#949ba4; margin-bottom:2px; }}
  .author {{ color:#fff; font-weight:600; }}
  .content {{ white-space:pre-wrap; word-wrap:break-word; }}
  .attachment {{ margin-top:4px; }}
  .attachment img {{ max-width:400px; max-height:300px; border-radius:6px; display:block; }}
  .attachment a {{ color:#00a8fc; }}
  footer {{ margin-top:20px; color:#949ba4; font-size:0.8em; }}
</style>
</head>
<body>
<h1>Transcript — {channel_name}</h1>
{messages}
<footer>{footer_text}</footer>
</body>
</html>
"""

_MSG_TEMPLATE = """<div class="msg">
  <img class="avatar" src="{avatar}" alt="">
  <div>
    <div class="meta"><span class="author">{author}</span> — {timestamp}</div>
    <div class="content">{content}</div>
    {attachments}
  </div>
</div>
"""


def _render_attachment(attachment: discord.Attachment) -> str:
    if attachment.content_type and attachment.content_type.startswith("image/"):
        return f'<div class="attachment"><img src="{html.escape(attachment.url)}"></div>'
    return f'<div class="attachment"><a href="{html.escape(attachment.url)}" target="_blank">📎 {html.escape(attachment.filename)}</a></div>'


async def _build_html(channel: discord.TextChannel) -> str:
    parts = []
    async for message in channel.history(limit=None, oldest_first=True):
        content = html.escape(message.content) if message.content else "<i>(pas de texte)</i>"
        attachments_html = "".join(_render_attachment(a) for a in message.attachments)
        parts.append(
            _MSG_TEMPLATE.format(
                avatar=html.escape(message.author.display_avatar.url),
                author=html.escape(str(message.author)),
                timestamp=message.created_at.strftime("%d/%m/%Y %H:%M"),
                content=content,
                attachments=attachments_html,
            )
        )
    count = len(parts)
    return _HTML_TEMPLATE.format(
        channel_name=html.escape(channel.name),
        messages="".join(parts) if parts else "<p><i>Aucun message.</i></p>",
        footer_text=f"Transcript généré — {count} message(s) exporté(s)",
    )


async def generate_and_send_transcript(channel: discord.TextChannel, owner_id: int, client: discord.Client):
    try:
        html_content = await _build_html(channel)
        filename = f"transcript-{channel.name}.html"

        if config.TICKET_TRANSCRIPT_SEND_TO_LOGS and config.TICKET_LOGS_CHANNEL:
            try:
                logs_channel = client.get_channel(config.TICKET_LOGS_CHANNEL) or await client.fetch_channel(
                    config.TICKET_LOGS_CHANNEL
                )
                file = discord.File(io.BytesIO(html_content.encode("utf-8")), filename=filename)
                await logs_channel.send(content=f"📄 Transcript du ticket **{channel.name}**", file=file)
            except (discord.NotFound, discord.Forbidden, discord.HTTPException) as exc:
                _log.error("Échec envoi salon logs: %s", exc)

        if config.TICKET_TRANSCRIPT_SEND_TO_OWNER_DM and owner_id:
            try:
                owner = client.get_user(owner_id) or await client.fetch_user(owner_id)
                file = discord.File(io.BytesIO(html_content.encode("utf-8")), filename=filename)
                await owner.send(content=f"📄 Voici le transcript de ton ticket **{channel.name}**.", file=file)
            except (discord.NotFound, discord.Forbidden, discord.HTTPException):
                _log.warning("Impossible d'envoyer le DM à %s (DMs fermés ?)", owner_id)

    except Exception as exc:
        _log.exception("Erreur lors de la génération du transcript")
        await log_action(client, "Erreur transcript", f"Impossible de générer le transcript pour {channel.name}: {exc}")
