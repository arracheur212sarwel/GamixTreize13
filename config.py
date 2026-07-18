"""
config.py
Configuration centralisée du bot unifié (Modération + AutoMod/Info/Logs +
Smash or Pass + Tickets), chargée depuis les variables d'environnement (.env).
"""

import json
import os

from dotenv import load_dotenv

load_dotenv()

TOKEN = os.getenv("DISCORD_TOKEN", "")
if not TOKEN:
    raise RuntimeError("La variable d'environnement DISCORD_TOKEN est manquante dans le fichier .env")

GUILD_ID = os.getenv("GUILD_ID")
GUILD_ID = int(GUILD_ID) if GUILD_ID else None

COLOR_SUCCESS = 0x57F287
COLOR_WARNING = 0xFEE75C
COLOR_ERROR = 0xED4245

TIMEOUT_DURATIONS = {
    "5m": 300,
    "10m": 600,
    "30m": 1800,
    "1h": 3600,
    "6h": 21600,
    "12h": 43200,
    "24h": 86400,
    "3d": 259200,
    "7d": 604800,
}

SOP_CHANNEL_ID = os.getenv("SOP_CHANNEL_ID")
SOP_CHANNEL_ID = int(SOP_CHANNEL_ID) if SOP_CHANNEL_ID else None

SOP_VOTE_DURATION_HOURS = int(os.getenv("SOP_VOTE_DURATION_HOURS", "48"))
SOP_CHECK_INTERVAL_MINUTES = int(os.getenv("SOP_CHECK_INTERVAL_MINUTES", "5"))

MEDIA_CHANNEL_ID = os.getenv("MEDIA_CHANNEL_ID")
MEDIA_CHANNEL_ID = int(MEDIA_CHANNEL_ID) if MEDIA_CHANNEL_ID else None

WELCOME_ROLE_ID = os.getenv("WELCOME_ROLE_ID")
WELCOME_ROLE_ID = int(WELCOME_ROLE_ID) if WELCOME_ROLE_ID else None

WELCOME_CHANNEL_ID = os.getenv("WELCOME_CHANNEL_ID")
WELCOME_CHANNEL_ID = int(WELCOME_CHANNEL_ID) if WELCOME_CHANNEL_ID else None

# --------------------------------------------------- Rôles par affinité
ACTIVE_ROLE_ID = os.getenv("ACTIVE_ROLE_ID")
ACTIVE_ROLE_ID = int(ACTIVE_ROLE_ID) if ACTIVE_ROLE_ID else None

MOD_PROPOSAL_CHANNEL_ID = os.getenv("MOD_PROPOSAL_CHANNEL_ID")
MOD_PROPOSAL_CHANNEL_ID = int(MOD_PROPOSAL_CHANNEL_ID) if MOD_PROPOSAL_CHANNEL_ID else None

VOICE_ACTIVITY_THRESHOLD_MINUTES = int(os.getenv("VOICE_ACTIVITY_THRESHOLD_MINUTES", "180"))

TICKET_LOGS_CHANNEL = os.getenv("TICKET_LOGS_CHANNEL")
TICKET_LOGS_CHANNEL = int(TICKET_LOGS_CHANNEL) if TICKET_LOGS_CHANNEL else None

TICKET_STAFF_ROLE = os.getenv("TICKET_STAFF_ROLE")
TICKET_STAFF_ROLE = int(TICKET_STAFF_ROLE) if TICKET_STAFF_ROLE else None

TICKET_EMBED_COLOR = os.getenv("TICKET_EMBED_COLOR", "#5865F2")
TICKET_FOOTER = os.getenv("TICKET_FOOTER", "Support")
TICKET_NAME_PREFIX = os.getenv("TICKET_NAME_PREFIX", "ticket")
TICKET_CLOSE_DELETE_DELAY_SECONDS = int(os.getenv("TICKET_CLOSE_DELETE_DELAY_SECONDS", "5"))
TICKET_CREATE_COOLDOWN_SECONDS = int(os.getenv("TICKET_CREATE_COOLDOWN_SECONDS", "30"))
TICKET_MAX_OPEN_PER_USER = int(os.getenv("TICKET_MAX_OPEN_PER_USER", "1"))

TICKET_TRANSCRIPT_SEND_TO_LOGS = os.getenv("TICKET_TRANSCRIPT_SEND_TO_LOGS", "true").lower() != "false"
TICKET_TRANSCRIPT_SEND_TO_OWNER_DM = os.getenv("TICKET_TRANSCRIPT_SEND_TO_OWNER_DM", "true").lower() != "false"

_DEFAULT_CATEGORIES = {
    "support": {"label": "Support", "emoji": "🛠️", "categoryId": None},
    "achat": {"label": "Achat", "emoji": "🛒", "categoryId": None},
    "partenariat": {"label": "Partenariat", "emoji": "🤝", "categoryId": None},
    "signalement": {"label": "Signalement", "emoji": "🚨", "categoryId": None},
    "autre": {"label": "Autre", "emoji": "❓", "categoryId": None},
}

_raw_categories = os.getenv("TICKET_CATEGORIES_JSON")
if _raw_categories:
    try:
        TICKET_CATEGORIES = json.loads(_raw_categories)
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"TICKET_CATEGORIES_JSON invalide (JSON mal formé) : {exc}")
else:
    TICKET_CATEGORIES = _DEFAULT_CATEGORIES