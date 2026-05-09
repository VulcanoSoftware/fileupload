import discord
from discord import app_commands
from discord.ui import Button, View, Modal, TextInput
from discord.ext import commands
import socket
import struct
import asyncio
import time
import re
import json
import os
import hashlib
import yaml
from datetime import datetime, timedelta
from discord.utils import utcnow
import pymongo

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_PATH = os.path.join(BASE_DIR, "config.yml")
DATA_DIR = os.path.join(BASE_DIR, "data")
os.makedirs(DATA_DIR, exist_ok=True)

MONGO_URI = os.environ.get("MONGO_URI")
MONGO_DB_NAME = os.environ.get("MONGO_DB_NAME", "thetimelord")

if pymongo is None:
    raise SystemExit("pymongo is required for MongoDB storage.")

if not MONGO_URI:
    raise SystemExit("MONGO_URI must be set for MongoDB storage.")

try:
    mongo_client = pymongo.MongoClient(MONGO_URI)
    mongo_db = mongo_client[MONGO_DB_NAME]
    levels_collection = mongo_db["levels"]
    punishments_collection = mongo_db["punishments"]
    settings_collection = mongo_db["settings"]
except Exception as e:
    raise SystemExit(f"Could not connect to MongoDB: {e}")

# Default configuration text that is written to config.yml when it does not exist yet.
# It uses JSON syntax for the real data and "#" comments to explain every setting.
DEFAULT_CONFIG_TEXT = """# The Time Lord bot configuration file
# Lines starting with '#' are comments and are ignored by the bot.
# All real data is written in JSON syntax below.

{
  # Global switch for the Minecraft whitelist / RCON system.
  # If this is false, whitelist commands and panels are disabled.
  "whitelist_enabled": true,

  "discord": {
    # Discord bot settings for this server.
    # Keep this file private and never share it with others.
    "token": "YOUR_DISCORD_BOT_TOKEN_HERE",

    # Prefix for old-style text commands (not slash-commands).
    "command_prefix": "!",

    # Activity type shown under the bot name.
    # Allowed values: playing, streaming, listening, watching, competing.
    "activity_type": "watching",

    # Text shown together with the activity type.
    "activity_text": "your watch"
  },

  "servers": {
    # Main Minecraft server that the bot can manage through RCON.
    "main": {
      # IP address or hostname of the Minecraft server.
      "host": "127.0.0.1",
      # RCON port configured in server.properties.
      "port": 25575,
      # RCON password for this server.
      "password": "YOUR_RCON_PASSWORD_HERE"
    },

    # Lobby or network server (optional).
    "lobby": {
      "host": "127.0.0.1",
      "port": 25575,
      "password": "YOUR_RCON_PASSWORD_HERE"
    },

    # KlokRise server (optional). You can rename or remove this if unused.
    "klokrise": {
      "host": "127.0.0.1",
      "port": 25575,
      "password": "YOUR_RCON_PASSWORD_HERE"
    }
  },

  "leveling": {
    # Automatic leveling based on chat activity.

    # Map each level number to a Discord role ID.
    # Fill this with the IDs of your level roles from Discord.
    "level_roles": {
      # "1": 123456789012345678,
      # "2": 234567890123456789
    },

    # How many unique messages are needed to gain one level.
    "unique_messages_per_level": 20,

    # Cooldown in seconds: messages faster than this do not count.
    "cooldown_seconds": 60,

    # Minimum number of days in the server before a user may reach level 4.
    "level4_min_days": 14,

    # Minimum number of days in the server before a user may reach level 5.
    "level5_min_days": 60,

    # How many recent message hashes are stored per user to detect repeats.
    "recent_message_hashes": 100,
    "leaderboard_admin_only": false,
    "auto_create_level_roles": false
  },

  "roles": {
    # Name of the Discord role that may manage the whitelist.
    "whitelist_permission": "whitelist_perms",

    # Name of the Discord role that may use admin level/moderation commands.
    "level_admin": "level_admin"
  },

  "messages": {
    # What the /time command should reply with.
    "time_response": "time is endless"
  },

  "commands": {
    # Turn individual slash commands on (true) or off (false).

    "amogus": false,
    "klokdag": false,
    "kloknacht": false,
    "lobby": false,
    "vulcanotechcraft": false,

    # Music helper command for VulcanoMusic.
    "musictip": true,

    # Simple message command.
    "time": true,

    # Moderation panel and commands.
    "moderation": true,
    "violations": true,
    "warnings": true,
    "clearwarnings": true,

    "timeout": true,
    "untimeout": true,
    "mute": true,
    "unmute": true,
    "setup": true,
    "kick": true,
    "ban": true,
    "unban": true,
    "clear": true,

    # Tools for fixing and managing level roles.
    "fixroles": true,

    # Whitelist management for Minecraft servers.
    "whitelist": true
  },

  "panel_buttons": {
    # Control which buttons appear in the /panel control panel.

    # Open the Minecraft whitelist manager.
    "whitelist_manager": true,

    # Open moderation settings and blocked word lists.
    "moderation_settings": true,

    # Show your own level, progress and member-since date.
    "my_level": true,

    # Show the top 10 players by level.
    "leaderboard": true,

    # Open the warnings management interface.
    "warnings_manager": true,

    # Quick access to the Active Developer badge info.
    "active_dev_badge": true,

    # Open the full setup and configuration interface.
    "more_settings": true,

    # Button to close the panel.
    "close_panel": true
  },

  "images": {
    # Image URLs used by fun commands like /amogus and /klokdag.
    # You can replace these URLs with your own hosted images.

    "amogus": "https://vulcanoimage.pages.dev/amogus.png",
    "klokdag": "https://vulcanoimage.pages.dev/klokdag.png",
    "kloknacht": "https://vulcanoimage.pages.dev/kloknacht.png",
    "lobby": "https://vulcanoimage.pages.dev/lobby.png",
    "vulcanotechcraft": "https://vulcanoimage.pages.dev/vulcanotechcraft.png"
  },

  "moderation": {
    # Moderation configuration that controls bad words, warnings and logs.

    # When any of these keywords appear in a message, the bot considers
    # the message as "directed at someone", which may trigger stricter rules.
    "direct_address_keywords": [
      " you ",
      " your ",
      " u ",
      " ya ",
      "@"
    ],

    # Categories define groups of words and how to handle them.
    "categories": {
      # Light category: less severe language, stricter when directed at a user.
      "light": {
        "words": [
          "fuck",
          "shit",
          "kankerzooi",
          "klootzak",
          "lul",
          "idioot",
          "kut",
          "klootzak",
          "tering",
          "kanker",
          "neuk",
          "neuken",
          "neuker",
          "fuck",
          "fucking",
          "shit",
          "tyfus",
          "mongool",
          "lul",
          "lullo",
          "eikel",
          "hoer",
          "slet",
          "bitch",
          "asshole",
          "motherfucker",
          "godverdomme",
          "verdomme",
          "ass",
          "asshole",
          "bastard",
          "bitch",
          "motherfucker",
          "cunt",
          "dick",
          "cock",
          "pussy",
          "slut",
          "whore",
          "damn",
          "goddamn",
          "retard",
          "jerk",
          "prick"
        ],
        # Only trigger this category when the message is directly
        # aimed at someone (mention or keyword above).
        "require_direct_address": true,
        # How many times a user may violate before max punishment in this category.
        "max_violations": 3,
        # How many days timeout to apply when limit is reached.
        "timeout_days": 1,
        # Whether the offending message should be deleted.
        "delete_message": true,
        # Whether the user should receive a DM when timed out.
        "dm_on_timeout": true
      },

      # Severe category: very heavy words, always punished regardless of direct address.
      "severe": {
        "words": [
          "kanker",
          "tyfus",
          "tering",
          "aids",
          "kkr",
          "kkrkanker"
        ],
        "require_direct_address": false,
        "max_violations": 1,
        "timeout_days": 1,
        "delete_message": true,
        "dm_on_timeout": true
      }
    },

    # Settings for direct timeouts (not just warnings).
    "dm": {
      "enabled": true,
      "message_template": "You have received a timeout of {duration} for: {reason}"
    },

    # Public messages that are sent in the channel when moderation happens.
    "public_messages": {
      "warning_enabled": true,
      "warning_template": "⚠️ {user} message removed due to language ({category}, warning {count}/{max}).",
      "timeout_template": "⏱️ {user} received a timeout of {duration} for: {reason}"
    },

    # Direct messages sent to the user for each violation (without timeout).
    "violation_dm": {
      "enabled": true,
      "message_template": "You have received a warning ({category}, warning {count}/{max}) for: {message}"
    },

    # Internal staff log channel configuration.
    "staff_log": {
      # Discord channel ID where staff log messages are posted.
      "channel_id": 0,
      "message_template": "[MOD] {user} violated rules in {channel} ({category}, warning {count}/{max}): {message}"
    }
  },

  "modbot": {
    # Additional per-guild settings used by the moderation helper commands
    # such as /mute, /unmute and /setup.
    "guilds": {
      # Use a string key with the Discord guild (server) ID.
      # Example:
      # "123456789012345678": {
      #   # ID of the role that should be used as the "Muted" role.
      #   # Users will receive this role when muted via the /mute command.
      #   "mute_role_id": 0,
      #
      #   # If true, the bot will automatically create a "Muted" role and
      #   # set basic channel permissions when you run /setup.
      #   "auto_create_muted_role": true
      # }
    }
  }
}
"""

# Automatically create a new configuration file with interactive prompts if it does not exist yet.
if not os.path.exists(CONFIG_PATH):
    print("No config.yml found. Starting first-time setup.")

    while True:
        token_input = input("Enter your Discord bot token: ").strip()
        if token_input:
            break
        print("Token cannot be empty. Please try again.")

    while True:
        whitelist_answer = input(
            "Enable the Minecraft whitelist system? (y/n, default y): "
        ).strip().lower()
        if whitelist_answer in ("", "y", "yes"):
            whitelist_enabled = True
            break
        if whitelist_answer in ("n", "no"):
            whitelist_enabled = False
            break
        print("Please answer with 'y' or 'n'.")

    main_host_input = ""
    main_port_value = 25575
    rcon_password_input = ""

    if whitelist_enabled:
        main_host_input = input(
            "Enter the main server host (default 127.0.0.1): "
        ).strip()
        if not main_host_input:
            main_host_input = "127.0.0.1"

        main_port_input = input(
            "Enter the main server RCON port (default 25575): "
        ).strip()
        try:
            main_port_value = int(main_port_input) if main_port_input else 25575
        except ValueError:
            main_port_value = 25575

        while True:
            rcon_password_input = input(
                "Enter the RCON password (used for all servers by default): "
            ).strip()
            if rcon_password_input:
                break
            print("RCON password cannot be empty. Please try again.")

    config_text = DEFAULT_CONFIG_TEXT
    config_text = config_text.replace("YOUR_DISCORD_BOT_TOKEN_HERE", token_input)

    if whitelist_enabled:
        config_text = config_text.replace(
            "\"host\": \"127.0.0.1\"", f"\"host\": \"{main_host_input}\"", 1
        )
        config_text = config_text.replace(
            "\"port\": 25575", f"\"port\": {main_port_value}", 1
        )
        config_text = config_text.replace(
            "YOUR_RCON_PASSWORD_HERE", rcon_password_input
        )
    else:
        config_text = config_text.replace(
            '"whitelist_enabled": true', '"whitelist_enabled": false'
        )

    while True:
        try:
            with open(CONFIG_PATH, "w", encoding="utf-8") as f:
                f.write(config_text)
            print(f"Written new config.yml to {CONFIG_PATH}.")
            break
        except OSError:
            print("Failed to write config.yml. Press Enter to retry or Ctrl+C to abort.")
            input()

# Read the configuration file contents.
with open(CONFIG_PATH, "r", encoding="utf-8") as f:
    _raw_config = f.read()

_config_lines = []
for _line in _raw_config.splitlines():
    _stripped = _line.lstrip()
    if _stripped.startswith("#") or _stripped == "":
        continue
    _config_lines.append(_line)

CONFIG = None
_json_text = "\n".join(_config_lines).strip()
if _json_text:
    try:
        CONFIG = json.loads(_json_text)
    except Exception:
        CONFIG = None

if not isinstance(CONFIG, dict):
    try:
        loaded = yaml.safe_load(_raw_config)
        if isinstance(loaded, dict):
            CONFIG = loaded
        else:
            raise ValueError("Config is not a valid mapping")
    except Exception as e:
        raise SystemExit(f"Failed to parse config.yml: {e}")

try:
    _config_doc = settings_collection.find_one({"_id": "config"})
    if _config_doc is not None:
        _config_data = _config_doc.get("data")
        if isinstance(_config_data, dict):
            file_token = None
            file_discord = CONFIG.get("discord")
            if isinstance(file_discord, dict):
                t = file_discord.get("token")
                if isinstance(t, str) and t.strip():
                    file_token = t
            merged = dict(CONFIG)
            def _merge(target, source, path=()):
                for key, value in source.items():
                    if path == ("discord",) and key == "token":
                        continue
                    if isinstance(value, dict) and isinstance(target.get(key), dict):
                        _merge(target[key], value, path + (key,))
                    else:
                        target[key] = value
            _merge(merged, _config_data)
            if file_token is not None:
                if not isinstance(merged.get("discord"), dict):
                    merged["discord"] = {}
                merged["discord"]["token"] = file_token
            CONFIG = merged
except Exception:
    pass

TOKEN = CONFIG["discord"]["token"]
COMMAND_PREFIX = CONFIG["discord"].get("command_prefix", "!")
ACTIVITY_TYPE_NAME = CONFIG["discord"].get("activity_type", "watching").lower()
ACTIVITY_TEXT = CONFIG["discord"].get("activity_text", "your watch")

WHITELIST_ENABLED = bool(CONFIG.get("whitelist_enabled", True))
COMMANDS_CONFIG = CONFIG.get("commands", {})
PANEL_BUTTONS_CONFIG = CONFIG.get("panel_buttons", {})

DEFAULT_COMMANDS = {
    "timeout": True,
    "untimeout": True,
    "mute": True,
    "unmute": True,
    "setup": True,
    "kick": True,
    "ban": True,
    "unban": True,
    "clear": True,
}

for _cmd_name, _default in DEFAULT_COMMANDS.items():
    if _cmd_name not in COMMANDS_CONFIG:
        COMMANDS_CONFIG[_cmd_name] = _default

if not WHITELIST_ENABLED:
    COMMANDS_CONFIG["whitelist"] = False
    PANEL_BUTTONS_CONFIG["whitelist_manager"] = False


def is_command_enabled(name: str) -> bool:
    return bool(COMMANDS_CONFIG.get(name, False))


def is_panel_button_enabled(name: str) -> bool:
    value = PANEL_BUTTONS_CONFIG.get(name)
    if value is None:
        return True
    return bool(value)

_servers_cfg = CONFIG.get("servers", {})
_main_cfg = _servers_cfg.get("main") if isinstance(_servers_cfg, dict) else None
_lobby_cfg = _servers_cfg.get("lobby") if isinstance(_servers_cfg, dict) else None
_klokrise_cfg = _servers_cfg.get("klokrise") if isinstance(_servers_cfg, dict) else None

if isinstance(_main_cfg, dict):
    MC_HOST = _main_cfg.get("host")
    MC_PORT = _main_cfg.get("port")
    MC_PASSWORD = _main_cfg.get("password")
else:
    MC_HOST = None
    MC_PORT = None
    MC_PASSWORD = None

if isinstance(_lobby_cfg, dict):
    LOBBY_HOST = _lobby_cfg.get("host")
    LOBBY_PORT = _lobby_cfg.get("port")
    LOBBY_PASSWORD = _lobby_cfg.get("password")
else:
    LOBBY_HOST = None
    LOBBY_PORT = None
    LOBBY_PASSWORD = None

if isinstance(_klokrise_cfg, dict):
    KLOCKRISE_HOST = _klokrise_cfg.get("host")
    KLOCKRISE_PORT = _klokrise_cfg.get("port")
    KLOCKRISE_PASSWORD = _klokrise_cfg.get("password")
else:
    KLOCKRISE_HOST = None
    KLOCKRISE_PORT = None
    KLOCKRISE_PASSWORD = None

LEVEL_ROLES = {int(level): role_id for level, role_id in CONFIG["leveling"]["level_roles"].items()}
# How many unique (non-duplicate) messages are needed for each level step.
UNIQUE_MESSAGES_PER_LEVEL = CONFIG["leveling"].get("unique_messages_per_level", 20)
# Cooldown in seconds: messages sent faster than this do not count for leveling.
MESSAGE_COOLDOWN_SECONDS = CONFIG["leveling"].get("cooldown_seconds", 60)
# Minimum membership duration (in days) required before a user may reach level 4.
LEVEL4_MIN_DAYS = CONFIG["leveling"].get("level4_min_days", 14)
LEVEL5_MIN_DAYS = CONFIG["leveling"].get("level5_min_days", 60)
RECENT_MESSAGE_HASHES = CONFIG["leveling"].get("recent_message_hashes", 100)
LEADERBOARD_ADMIN_ONLY = bool(
    CONFIG["leveling"].get("leaderboard_admin_only", False)
)

# Name of the role that grants access to whitelist management features.
WHITELIST_PERMISSION_ROLE = CONFIG["roles"].get("whitelist_permission", "whitelist_perms")
# Name of the role that grants access to admin-only level and moderation commands.
LEVEL_ADMIN_ROLE = CONFIG["roles"].get("level_admin", "level_admin")

# Text used by the /time command when the bot replies.
TIME_RESPONSE_TEXT = CONFIG["messages"].get("time_response", "time is endless")

IMAGES = CONFIG.get("images", {})
MAX_LEVEL_ROLE = max(LEVEL_ROLES.keys(), default=0)


def get_auto_create_level_roles() -> bool:
    leveling_cfg = CONFIG.get("leveling")
    if not isinstance(leveling_cfg, dict):
        return False
    return bool(leveling_cfg.get("auto_create_level_roles", False))


def set_auto_create_level_roles(value: bool) -> None:
    leveling_cfg = CONFIG.get("leveling")
    if not isinstance(leveling_cfg, dict):
        leveling_cfg = {}
        CONFIG["leveling"] = leveling_cfg
    leveling_cfg["auto_create_level_roles"] = bool(value)
    save_config()


def set_level_role_mapping(level: int, role_id: int | None) -> None:
    global LEVEL_ROLES, MAX_LEVEL_ROLE
    leveling_cfg = CONFIG.get("leveling")
    if not isinstance(leveling_cfg, dict):
        leveling_cfg = {}
        CONFIG["leveling"] = leveling_cfg
    roles_cfg = leveling_cfg.get("level_roles")
    if not isinstance(roles_cfg, dict):
        roles_cfg = {}
        leveling_cfg["level_roles"] = roles_cfg
    key = str(level)
    if role_id is None:
        roles_cfg.pop(key, None)
        LEVEL_ROLES.pop(level, None)
    else:
        roles_cfg[key] = int(role_id)
        LEVEL_ROLES[level] = int(role_id)
    MAX_LEVEL_ROLE = max(LEVEL_ROLES.keys(), default=0)
    save_config()

# Moderation configuration describing forbidden words and how to handle them.
MODERATION_CONFIG = CONFIG.get("moderation", {})

MODBOT_CONFIG = CONFIG.get("modbot")
if not isinstance(MODBOT_CONFIG, dict):
    MODBOT_CONFIG = {"guilds": {}}
    CONFIG["modbot"] = MODBOT_CONFIG

MODBOT_GUILDS = MODBOT_CONFIG.get("guilds")
if not isinstance(MODBOT_GUILDS, dict):
    MODBOT_GUILDS = {}
    MODBOT_CONFIG["guilds"] = MODBOT_GUILDS

DIRECT_ADDRESS_KEYWORDS = MODERATION_CONFIG.get(
    "direct_address_keywords",
    [
        " you ",
        " your ",
        " u ",
        " ya ",
        "@",
    ],
)

MODERATION_CATEGORIES = MODERATION_CONFIG.get("categories")

if not MODERATION_CATEGORIES:
    light_words_fallback = MODERATION_CONFIG.get(
        "light_swear_words",
        [
            "fuck",
            "shit",
            "kankerzooi",
            "klootzak",
            "lul",
            "idioot",
        ],
    )
    severe_words_fallback = MODERATION_CONFIG.get(
        "severe_swear_words",
        [
            "kanker",
            "tyfus",
            "tering",
            "aids",
            "kkr",
            "kkrkanker",
        ],
    )
    max_minor_violations_fallback = int(MODERATION_CONFIG.get("max_minor_violations", 3))
    timeout_days_fallback = float(MODERATION_CONFIG.get("timeout_days", 1))
    MODERATION_CATEGORIES = {
        "light": {
            "words": light_words_fallback,
            "require_direct_address": True,
            "max_violations": max_minor_violations_fallback,
            "timeout_days": timeout_days_fallback,
            "delete_message": True,
            "dm_on_timeout": True,
        },
        "severe": {
            "words": severe_words_fallback,
            "require_direct_address": False,
            "max_violations": 1,
            "timeout_days": timeout_days_fallback,
            "delete_message": True,
            "dm_on_timeout": True,
        },
    }

def has_level_admin_role(member: discord.Member) -> bool:
    if member.guild_permissions.administrator:
        return True
    return any(role.name == LEVEL_ADMIN_ROLE for role in member.roles)

PUBLIC_MESSAGES_CONFIG = MODERATION_CONFIG.get("public_messages", {})
PUBLIC_WARNING_ENABLED = bool(PUBLIC_MESSAGES_CONFIG.get("warning_enabled", True))
PUBLIC_WARNING_TEMPLATE = PUBLIC_MESSAGES_CONFIG.get(
    "warning_template",
    "⚠️ {user} message removed due to language ({category}, warning {count}/{max}).",
)

VIOLATION_DM_CONFIG = MODERATION_CONFIG.get("violation_dm", {})
VIOLATION_DM_ENABLED = bool(VIOLATION_DM_CONFIG.get("enabled", True))
VIOLATION_DM_TEMPLATE = VIOLATION_DM_CONFIG.get(
    "message_template",
    "You have received a warning ({category}, warning {count}/{max}) for: {message}",
)

STAFF_LOG_CONFIG = MODERATION_CONFIG.get("staff_log", {})
STAFF_LOG_CHANNEL_ID = int(STAFF_LOG_CONFIG.get("channel_id", 0))
STAFF_LOG_TEMPLATE = STAFF_LOG_CONFIG.get(
    "message_template",
    "[MOD] {user} violated rules in {channel} ({category}, warning {count}/{max}): {message}",
)


def reload_config_state():
    global TOKEN, COMMAND_PREFIX, ACTIVITY_TYPE_NAME, ACTIVITY_TEXT
    global WHITELIST_ENABLED, COMMANDS_CONFIG, PANEL_BUTTONS_CONFIG
    global MC_HOST, MC_PORT, MC_PASSWORD
    global LOBBY_HOST, LOBBY_PORT, LOBBY_PASSWORD
    global KLOCKRISE_HOST, KLOCKRISE_PORT, KLOCKRISE_PASSWORD
    global LEVEL_ROLES, UNIQUE_MESSAGES_PER_LEVEL, MESSAGE_COOLDOWN_SECONDS
    global LEVEL4_MIN_DAYS, LEVEL5_MIN_DAYS, RECENT_MESSAGE_HASHES
    global LEADERBOARD_ADMIN_ONLY
    global WHITELIST_PERMISSION_ROLE, LEVEL_ADMIN_ROLE
    global TIME_RESPONSE_TEXT, IMAGES, MAX_LEVEL_ROLE
    global MODERATION_CONFIG, MODBOT_CONFIG, MODBOT_GUILDS
    global DIRECT_ADDRESS_KEYWORDS, MODERATION_CATEGORIES
    global PUBLIC_MESSAGES_CONFIG, PUBLIC_WARNING_ENABLED, PUBLIC_WARNING_TEMPLATE
    global VIOLATION_DM_CONFIG, VIOLATION_DM_ENABLED, VIOLATION_DM_TEMPLATE
    global STAFF_LOG_CONFIG, STAFF_LOG_CHANNEL_ID, STAFF_LOG_TEMPLATE

    TOKEN = CONFIG["discord"]["token"]
    COMMAND_PREFIX = CONFIG["discord"].get("command_prefix", "!")
    ACTIVITY_TYPE_NAME = CONFIG["discord"].get("activity_type", "watching").lower()
    ACTIVITY_TEXT = CONFIG["discord"].get("activity_text", "your watch")

    WHITELIST_ENABLED = bool(CONFIG.get("whitelist_enabled", True))
    COMMANDS_CONFIG = CONFIG.get("commands", {})
    PANEL_BUTTONS_CONFIG = CONFIG.get("panel_buttons", {})

    default_commands = {
        "timeout": True,
        "untimeout": True,
        "mute": True,
        "unmute": True,
        "setup": True,
        "kick": True,
        "ban": True,
        "unban": True,
        "clear": True,
    }

    for name, enabled in default_commands.items():
        if name not in COMMANDS_CONFIG:
            COMMANDS_CONFIG[name] = enabled

    if not WHITELIST_ENABLED:
        COMMANDS_CONFIG["whitelist"] = False
        PANEL_BUTTONS_CONFIG["whitelist_manager"] = False

    servers_cfg = CONFIG.get("servers", {})
    main_cfg = servers_cfg.get("main") if isinstance(servers_cfg, dict) else None
    lobby_cfg = servers_cfg.get("lobby") if isinstance(servers_cfg, dict) else None
    klokrise_cfg = servers_cfg.get("klokrise") if isinstance(servers_cfg, dict) else None

    if isinstance(main_cfg, dict):
        MC_HOST = main_cfg.get("host")
        MC_PORT = main_cfg.get("port")
        MC_PASSWORD = main_cfg.get("password")
    else:
        MC_HOST = None
        MC_PORT = None
        MC_PASSWORD = None

    if isinstance(lobby_cfg, dict):
        LOBBY_HOST = lobby_cfg.get("host")
        LOBBY_PORT = lobby_cfg.get("port")
        LOBBY_PASSWORD = lobby_cfg.get("password")
    else:
        LOBBY_HOST = None
        LOBBY_PORT = None
        LOBBY_PASSWORD = None

    if isinstance(klokrise_cfg, dict):
        KLOCKRISE_HOST = klokrise_cfg.get("host")
        KLOCKRISE_PORT = klokrise_cfg.get("port")
        KLOCKRISE_PASSWORD = klokrise_cfg.get("password")
    else:
        KLOCKRISE_HOST = None
        KLOCKRISE_PORT = None
        KLOCKRISE_PASSWORD = None

    LEVEL_ROLES = {
        int(level): role_id
        for level, role_id in CONFIG["leveling"]["level_roles"].items()
    }
    UNIQUE_MESSAGES_PER_LEVEL = CONFIG["leveling"].get(
        "unique_messages_per_level", 20
    )
    MESSAGE_COOLDOWN_SECONDS = CONFIG["leveling"].get("cooldown_seconds", 60)
    LEVEL4_MIN_DAYS = CONFIG["leveling"].get("level4_min_days", 14)
    LEVEL5_MIN_DAYS = CONFIG["leveling"].get("level5_min_days", 60)
    RECENT_MESSAGE_HASHES = CONFIG["leveling"].get("recent_message_hashes", 100)
    LEADERBOARD_ADMIN_ONLY = bool(
        CONFIG["leveling"].get("leaderboard_admin_only", False)
    )

    WHITELIST_PERMISSION_ROLE = CONFIG["roles"].get(
        "whitelist_permission", "whitelist_perms"
    )
    LEVEL_ADMIN_ROLE = CONFIG["roles"].get("level_admin", "level_admin")

    TIME_RESPONSE_TEXT = CONFIG["messages"].get(
        "time_response", "time is endless"
    )

    IMAGES = CONFIG.get("images", {})
    MAX_LEVEL_ROLE = max(LEVEL_ROLES.keys(), default=0)

    MODERATION_CONFIG = CONFIG.get("moderation", {})

    MODBOT_CONFIG = CONFIG.get("modbot")
    if not isinstance(MODBOT_CONFIG, dict):
        MODBOT_CONFIG = {"guilds": {}}
        CONFIG["modbot"] = MODBOT_CONFIG

    MODBOT_GUILDS = MODBOT_CONFIG.get("guilds")
    if not isinstance(MODBOT_GUILDS, dict):
        MODBOT_GUILDS = {}
        MODBOT_CONFIG["guilds"] = MODBOT_GUILDS

    DIRECT_ADDRESS_KEYWORDS = MODERATION_CONFIG.get(
        "direct_address_keywords",
        [
            " you ",
            " your ",
            " u ",
            " ya ",
            "@",
        ],
    )

    MODERATION_CATEGORIES = MODERATION_CONFIG.get("categories")

    if not MODERATION_CATEGORIES:
        light_words_fallback = MODERATION_CONFIG.get(
            "light_swear_words",
            [
                "fuck",
                "shit",
                "kankerzooi",
                "klootzak",
                "lul",
                "idioot",
            ],
        )
        severe_words_fallback = MODERATION_CONFIG.get(
            "severe_swear_words",
            [
                "kanker",
                "tyfus",
                "tering",
                "aids",
                "kkr",
                "kkrkanker",
            ],
        )
        max_minor_violations_fallback = int(
            MODERATION_CONFIG.get("max_minor_violations", 3)
        )
        timeout_days_fallback = float(
            MODERATION_CONFIG.get("timeout_days", 1)
        )
        MODERATION_CATEGORIES = {
            "light": {
                "words": light_words_fallback,
                "require_direct_address": True,
                "max_violations": max_minor_violations_fallback,
                "timeout_days": timeout_days_fallback,
                "delete_message": True,
                "dm_on_timeout": True,
            },
            "severe": {
                "words": severe_words_fallback,
                "require_direct_address": False,
                "max_violations": 1,
                "timeout_days": timeout_days_fallback,
                "delete_message": True,
                "dm_on_timeout": True,
            },
        }

    PUBLIC_MESSAGES_CONFIG = MODERATION_CONFIG.get("public_messages", {})
    PUBLIC_WARNING_ENABLED = bool(
        PUBLIC_MESSAGES_CONFIG.get("warning_enabled", True)
    )
    PUBLIC_WARNING_TEMPLATE = PUBLIC_MESSAGES_CONFIG.get(
        "warning_template",
        "⚠️ {user} message removed due to language ({category}, warning {count}/{max}).",
    )

    VIOLATION_DM_CONFIG = MODERATION_CONFIG.get("violation_dm", {})
    VIOLATION_DM_ENABLED = bool(VIOLATION_DM_CONFIG.get("enabled", True))
    VIOLATION_DM_TEMPLATE = VIOLATION_DM_CONFIG.get(
        "message_template",
        "You have received a warning ({category}, warning {count}/{max}) for: {message}",
    )

    STAFF_LOG_CONFIG = MODERATION_CONFIG.get("staff_log", {})
    STAFF_LOG_CHANNEL_ID = int(STAFF_LOG_CONFIG.get("channel_id", 0))
    STAFF_LOG_TEMPLATE = STAFF_LOG_CONFIG.get(
        "message_template",
        "[MOD] {user} violated rules in {channel} ({category}, warning {count}/{max}): {message}",
    )

    try:
        changed = False
        if isinstance(MODERATION_CATEGORIES, dict):
            for cname, ccfg in MODERATION_CATEGORIES.items():
                if not isinstance(ccfg, dict):
                    continue
                words = ccfg.get("words")
                if not isinstance(words, list):
                    continue
                case_sensitive = bool(ccfg.get("case_sensitive", False))
                seen = set()
                result: list[str] = []
                for w in words:
                    s = str(w)
                    k = s if case_sensitive else s.lower()
                    if k not in seen:
                        seen.add(k)
                        result.append(s if case_sensitive else k)
                if result != words:
                    ccfg["words"] = result
                    changed = True
        if changed:
            save_config()
    except Exception:
        pass

def load_levels():
    try:
        loaded = {}
        for doc in levels_collection.find({}):
            user_id = str(doc.get("_id"))
            if not user_id:
                continue
            entry = dict(doc)
            entry.pop("_id", None)
            loaded[user_id] = entry
        return loaded
    except Exception:
        return {}


levels = load_levels()

def save_levels():
    cleaned_levels = {}
    for user_id, data in levels.items():
        if not isinstance(data, dict):
            continue
        entry = dict(data)
        for key in ("level", "unique_count"):
            if key in entry:
                entry[key] = int(entry[key])
        for key in ("join_date", "last_message_time"):
            if key in entry:
                entry[key] = int(entry[key])
        cleaned_levels[user_id] = entry
    try:
        for user_id, entry in cleaned_levels.items():
            doc = dict(entry)
            doc["_id"] = str(user_id)
            levels_collection.replace_one({"_id": doc["_id"]}, doc, upsert=True)
    except Exception:
        return

def save_config():
    try:
        default_lines = []
        for line in DEFAULT_CONFIG_TEXT.splitlines():
            stripped = line.lstrip()
            if stripped.startswith("#") or stripped == "":
                continue
            default_lines.append(line)
        default_json_text = "\n".join(default_lines).strip()
        try:
            default_dict = json.loads(default_json_text) if default_json_text else {}
        except Exception:
            default_dict = {}
        default_order = list(default_dict.keys())

        template_lines = DEFAULT_CONFIG_TEXT.splitlines()
        top_keys: list[tuple[int, str]] = []
        for idx, line in enumerate(template_lines):
            m = re.match(r'\s*"([^"]+)":', line)
            if m and line.startswith('  "'):
                top_keys.append((idx, m.group(1)))

        header_comments: list[str] = []
        key_comments: dict[str, list[str]] = {}

        if top_keys:
            first_idx = top_keys[0][0]
            for i in range(first_idx):
                if template_lines[i].lstrip().startswith("#"):
                    header_comments.append(template_lines[i])

            for pos, (start_idx, key) in enumerate(top_keys):
                end_idx = top_keys[pos + 1][0] if pos + 1 < len(top_keys) else len(template_lines)
                comments: list[str] = []
                for j in range(start_idx, end_idx):
                    if template_lines[j].lstrip().startswith("#"):
                        comments.append(template_lines[j])
                if comments:
                    key_comments[key] = comments

        lines: list[str] = []
        if header_comments:
            lines.extend(header_comments)
            lines.append("")
        lines.append("{")

        keys_to_write: list[str] = []
        for k in default_order:
            if k in CONFIG:
                keys_to_write.append(k)
        for k in CONFIG.keys():
            if k not in keys_to_write:
                keys_to_write.append(k)

        total_keys = len(keys_to_write)
        for idx, key in enumerate(keys_to_write):
            value = CONFIG[key]
            key_block: list[str] = []
            comments = key_comments.get(key)
            if comments:
                key_block.extend(comments)
            chunk_lines = json.dumps({key: value}, indent=2, ensure_ascii=False).splitlines()
            inner_lines = chunk_lines[1:-1]
            key_block.extend(inner_lines)
            if idx != total_keys - 1 and key_block:
                key_block[-1] = key_block[-1] + ","
            lines.extend(key_block)

        lines.append("}")
        lines.append("")
        full_text = "\n".join(lines)
        with open(CONFIG_PATH, "w", encoding="utf-8") as f:
            f.write(full_text)
        try:
            safe_data = dict(CONFIG)
            dc = safe_data.get("discord")
            if isinstance(dc, dict):
                dc_copy = dict(dc)
                dc_copy.pop("token", None)
                safe_data["discord"] = dc_copy
            settings_collection.replace_one(
                {"_id": "config"},
                {"_id": "config", "data": safe_data},
                upsert=True,
            )
        except Exception:
            pass
    except Exception:
        pass


def get_config_template_top_level_info() -> tuple[list[str], dict[str, str]]:
    template_lines = DEFAULT_CONFIG_TEXT.splitlines()
    top_keys: list[tuple[int, str]] = []
    for idx, line in enumerate(template_lines):
        m = re.match(r'\s*"([^"]+)":', line)
        if m and line.startswith('  "'):
            top_keys.append((idx, m.group(1)))
    order: list[str] = []
    comments_map: dict[str, str] = {}
    if top_keys:
        for pos, (start_idx, key) in enumerate(top_keys):
            order.append(key)
            end_idx = (
                top_keys[pos + 1][0]
                if pos + 1 < len(top_keys)
                else len(template_lines)
            )
            comment_lines: list[str] = []
            for j in range(start_idx, end_idx):
                stripped = template_lines[j].lstrip()
                if stripped.startswith("#"):
                    text = stripped[1:].lstrip()
                    comment_lines.append(text)
            if comment_lines:
                comments_map[key] = "\n".join(comment_lines)
    return order, comments_map


def get_top_level_comment_text(section_name: str) -> str:
    _, comments_map = get_config_template_top_level_info()
    return comments_map.get(section_name, "")


def _merge_config_defaults(target: dict, defaults: dict, path: tuple = ()) -> bool:
    changed = False
    for key, default_value in defaults.items():
        if key not in target:
            if path in (("images",), ("servers",)):
                continue
            target[key] = default_value
            changed = True
        else:
            current_value = target[key]
            if isinstance(current_value, dict) and isinstance(default_value, dict):
                if _merge_config_defaults(current_value, default_value, path + (key,)):
                    changed = True
    return changed


def _overlay_user_defaults(defaults: dict, user_config: dict, path: tuple = ()) -> None:
    for key, user_value in user_config.items():
        if key not in defaults:
            continue
        if path == ("discord",) and key == "token":
            continue
        default_value = defaults[key]
        if isinstance(default_value, dict) and isinstance(user_value, dict):
            _overlay_user_defaults(default_value, user_value, path + (key,))
        else:
            defaults[key] = user_value


def ensure_config_comments_and_defaults():
    global CONFIG
    try:
        default_lines = []
        for line in DEFAULT_CONFIG_TEXT.splitlines():
            stripped = line.lstrip()
            if stripped.startswith("#") or stripped == "":
                continue
            default_lines.append(line)
        default_json_text = "\n".join(default_lines).strip()
        default_dict = json.loads(default_json_text) if default_json_text else {}
    except Exception:
        default_dict = {}

    changed = False
    if isinstance(CONFIG, dict) and isinstance(default_dict, dict) and default_dict:
        _overlay_user_defaults(default_dict, CONFIG)
        if _merge_config_defaults(CONFIG, default_dict):
            changed = True

    has_comment = False
    for line in _raw_config.splitlines():
        if line.lstrip().startswith("#"):
            has_comment = True
            break

    if not has_comment:
        changed = True

    if changed:
        save_config()

ensure_config_comments_and_defaults()

try:
    # One-time normalization at startup to remove duplicate blocked words.
    reload_config_state()
except Exception:
    pass

def load_punishments():
    try:
        data = {}
        for doc in punishments_collection.find({}):
            key = str(doc.get("_id"))
            events = doc.get("events", [])
            if isinstance(events, list):
                data[key] = events
        return data
    except Exception:
        return {}


def save_punishments(data):
    try:
        for key, events in data.items():
            if not isinstance(events, list):
                continue
            doc = {"_id": str(key), "events": events}
            punishments_collection.replace_one({"_id": doc["_id"]}, doc, upsert=True)
    except Exception:
        return


EVENT_TYPE_CODES = {
    "timeout_set": 1,
    "timeout_removed": 2,
    "mute_set": 3,
    "mute_removed": 4,
    "ban_set": 5,
    "ban_removed": 6,
}

EVENT_TYPE_NAMES = {v: k for k, v in EVENT_TYPE_CODES.items()}


def normalize_punishment_entry(entry: dict) -> bool:
    changed = False
    ts = entry.get("timestamp")
    if isinstance(ts, str):
        try:
            dt = datetime.fromisoformat(ts)
            entry["timestamp"] = int(dt.timestamp())
            changed = True
        except Exception:
            pass
    event = entry.get("event_type")
    if isinstance(event, str):
        code = EVENT_TYPE_CODES.get(event)
        if code is not None:
            entry["event_type"] = code
            changed = True
    duration_seconds = entry.get("duration_seconds")
    if duration_seconds is None:
        minutes = entry.get("duration_minutes")
        if isinstance(minutes, (int, float)):
            entry["duration_seconds"] = int(minutes * 60)
            changed = True
        if "duration_minutes" in entry:
            del entry["duration_minutes"]
            changed = True
        if "duration_text" in entry:
            del entry["duration_text"]
            changed = True
    reason = entry.get("reason")
    if isinstance(reason, str):
        lowered = reason.strip().lower()
        if lowered in ("no reason provided", "geen reden opgegeven", ""):
            entry["reason"] = None
            changed = True
    return changed


def normalize_punishments_structure(data: dict) -> dict:
    changed = False
    for guild_id, events in list(data.items()):
        if not isinstance(events, list):
            continue
        for entry in events:
            if isinstance(entry, dict):
                if normalize_punishment_entry(entry):
                    changed = True
    if changed:
        save_punishments(data)
    return data


punishments = normalize_punishments_structure(load_punishments())


def get_modbot_guild_config(guild_id: int):
    key = str(guild_id)
    if key not in MODBOT_GUILDS:
        MODBOT_GUILDS[key] = {
            "mute_role_id": None,
            "auto_create_muted_role": False,
        }
        save_config()
    return MODBOT_GUILDS[key]


def log_punishment(guild_id: int, user_id: int, event_type: str, info: dict):
    key = str(guild_id)
    if key not in punishments:
        punishments[key] = []
    info_copy = dict(info)
    duration_seconds = None
    if "duration_seconds" in info_copy:
        value = info_copy.pop("duration_seconds")
        if isinstance(value, (int, float)):
            duration_seconds = int(value)
    elif "duration_minutes" in info_copy:
        minutes = info_copy.pop("duration_minutes")
        if isinstance(minutes, (int, float)):
            duration_seconds = int(minutes * 60)
    if "duration_text" in info_copy:
        info_copy.pop("duration_text")
    reason = info_copy.get("reason")
    if isinstance(reason, str):
        lowered = reason.strip().lower()
        if lowered in ("no reason provided", "geen reden opgegeven", ""):
            info_copy["reason"] = None
    code = EVENT_TYPE_CODES.get(event_type)
    stored_event = code if code is not None else event_type
    entry = {
        "user_id": user_id,
        "event_type": stored_event,
        "timestamp": int(utcnow().timestamp()),
    }
    if duration_seconds is not None and duration_seconds > 0:
        entry["duration_seconds"] = duration_seconds
    entry.update(info_copy)
    punishments[key].append(entry)
    save_punishments(punishments)


UNIT_TO_SECONDS = {
    "seconds": 1,
    "minutes": 60,
    "hours": 60 * 60,
    "days": 60 * 60 * 24,
    "weeks": 60 * 60 * 24 * 7,
    "months": 60 * 60 * 24 * 30,
    "years": 60 * 60 * 24 * 365,
}

UNIT_LABELS = {
    "seconds": ("second", "seconds"),
    "minutes": ("minute", "minutes"),
    "hours": ("hour", "hours"),
    "days": ("day", "days"),
    "weeks": ("week", "weeks"),
    "months": ("month", "months"),
    "years": ("year", "years"),
}


def get_duration_info(value: int, unit: str):
    seconds_per_unit = UNIT_TO_SECONDS.get(unit, 60)
    total_seconds = value * seconds_per_unit
    singular, plural = UNIT_LABELS.get(unit, ("unit", "units"))
    label = singular if value == 1 else plural
    text = f"{value} {label}"
    return total_seconds, text


async def send_punishment_dm(
    user: discord.abc.User,
    guild: discord.Guild,
    title: str,
    description: str,
):
    try:
        if user.bot:
            return
        embed = discord.Embed(title=title, description=description, color=discord.Color.red())
        embed.set_footer(text=guild.name)
        await user.send(embed=embed)
    except discord.Forbidden:
        return
    except Exception:
        return


async def send_info_dm(
    user: discord.abc.User,
    guild: discord.Guild,
    title: str,
    description: str,
):
    try:
        if user.bot:
            return
        embed = discord.Embed(title=title, description=description, color=discord.Color.green())
        embed.set_footer(text=guild.name)
        await user.send(embed=embed)
    except discord.Forbidden:
        return
    except Exception:
        return


async def ensure_muted_role(guild: discord.Guild):
    guild_conf = get_modbot_guild_config(guild.id)
    mute_role_id = guild_conf.get("mute_role_id")
    role = None

    if mute_role_id:
        role = guild.get_role(mute_role_id)
        if role is not None:
            return role

    role = discord.utils.get(guild.roles, name="Muted")
    if role is not None:
        guild_conf["mute_role_id"] = role.id
        save_config()
        return role

    if not guild_conf.get("auto_create_muted_role", False):
        return None

    role = await guild.create_role(name="Muted", reason="Muted role for /mute")
    for channel in guild.channels:
        overwrite = channel.overwrites_for(role)
        overwrite.send_messages = False
        overwrite.add_reactions = False
        overwrite.speak = False
        try:
            await channel.set_permissions(role, overwrite=overwrite)
        except Exception:
            continue

    guild_conf["mute_role_id"] = role.id
    save_config()
    return role


async def schedule_timeout_end(guild_id: int, user_id: int, duration_seconds: int):
    await asyncio.sleep(duration_seconds)
    guild = bot.get_guild(guild_id)
    if guild is None:
        return
    try:
        member = guild.get_member(user_id)
        if member is None:
            return
        if member.communication_disabled_until is not None and member.communication_disabled_until > utcnow():
            return
        key = str(guild.id)
        events = punishments.get(key, [])
        already_removed = False
        for e in events:
            if e.get("user_id") != user_id:
                continue
            et = e.get("event_type")
            if et == "timeout_removed":
                already_removed = True
                break
            if isinstance(et, int) and EVENT_TYPE_NAMES.get(et) == "timeout_removed":
                already_removed = True
                break
        if already_removed:
            return
        description = (
            f"Your timeout in {guild.name} has expired.\n"
            f"Reason: End of timeout"
        )
        await send_info_dm(member, guild, "Timeout expired", description)
        log_punishment(
            guild.id,
            member.id,
            "timeout_removed",
            {
                "reason": "End of timeout",
                "automatic": True,
            },
        )
    except discord.Forbidden:
        return
    except Exception:
        return


async def schedule_unban(guild_id: int, user_id: int, duration_seconds: int):
    await asyncio.sleep(duration_seconds)
    guild = bot.get_guild(guild_id)
    if guild is None:
        return
    try:
        user = await bot.fetch_user(user_id)
    except Exception:
        return

    try:
        await guild.unban(user, reason="End of temporary ban")
        description = (
            f"Your temporary ban in {guild.name} has expired.\n"
            f"Reason: End of temporary ban"
        )
        await send_info_dm(user, guild, "Unban", description)
        log_punishment(
            guild.id,
            user.id,
            "ban_removed",
            {
                "reason": "End of temporary ban",
                "automatic": True,
            },
        )
    except discord.NotFound:
        return
    except discord.Forbidden:
        return
    except Exception:
        return


async def schedule_unmute(guild_id: int, user_id: int, duration_seconds: int):
    await asyncio.sleep(duration_seconds)
    guild = bot.get_guild(guild_id)
    if guild is None:
        return
    member = guild.get_member(user_id)
    if member is None:
        return
    muted_role = await ensure_muted_role(guild)
    if muted_role is None:
        return
    if muted_role not in member.roles:
        return
    try:
        await member.remove_roles(muted_role, reason="End of mute")
        description = (
            f"Your mute in {guild.name} has expired.\n"
            f"Reason: End of mute"
        )
        await send_info_dm(member, guild, "Unmute", description)
        log_punishment(
            guild.id,
            member.id,
            "mute_removed",
            {
                "reason": "End of mute",
                "automatic": True,
            },
        )
    except discord.Forbidden:
        return
    except Exception:
        return

def required_uniques_for_level(level: int) -> int:
    """
    Calculate how many unique messages are required to reach a given level.

    The amount is simply the base number from the configuration multiplied
    by the target level number.
    """
    return UNIQUE_MESSAGES_PER_LEVEL * level

def message_hash(content: str) -> str:
    return hashlib.sha256(content.encode("utf-8")).hexdigest()[:16]

def ensure_user_schema(user_id: str, join_date_default: float | None = None):
    """
    Make sure that the stored data for a user has all the expected fields.

    This is important because older versions of the bot may have stored the
    data in a slightly different format. By normalizing the structure here,
    all later code can safely assume the same keys exist.
    """
    if user_id not in levels:
        return
    data = levels[user_id]
    if "unique_count" not in data:
        messages = data.get("unique_messages", [])
        if isinstance(messages, list):
            data["unique_count"] = len(messages)
        else:
            data["unique_count"] = 0
    if "recent_hashes" not in data:
        data["recent_hashes"] = []
    if "join_date" not in data and join_date_default is not None:
        data["join_date"] = join_date_default
    if "unique_messages" in data:
        del data["unique_messages"]
    if "violations" not in data:
        data["violations"] = {}
    elif isinstance(data["violations"], int):
        data["violations"] = {"_all": data["violations"]}

class MCRcon:
    """
    Small helper class to talk to a Minecraft server over RCON.

    It takes care of connecting, authenticating and sending commands, so the
    rest of the bot can simply ask for a command to be run and receive the
    text response from the server.
    """
    def __init__(self, host, port, password):
        self.host = host
        self.port = port
        self.password = password
        self.socket = None
        self.request_id = 0

    def connect(self):
        """Open a TCP connection to the RCON server and authenticate."""
        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.settimeout(5)
            self.socket.connect((self.host, self.port))
            self._send(3, self.password)
            response = self._receive()
            if response['request_id'] == -1:
                raise Exception("Authentication failed: wrong password")
            return True
        except Exception as e:
            self.disconnect()
            return False, str(e)

    def disconnect(self):
        """Close the TCP connection to the RCON server if it is open."""
        if self.socket:
            self.socket.close()
            self.socket = None

    def send_command(self, command: str) -> str:
        """
        Send a single command to the RCON server and return its response text.

        If there is no active connection yet, this method will first try to
        connect and authenticate using the stored host, port and password.
        """
        if not self.socket:
            result = self.connect()
            if isinstance(result, tuple) and not result[0]:
                return f"Not connected to server: {result[1]}"
            elif not result:
                return "Not connected to server."
        
        try:
            self._send(2, command)
            response = self._receive()
            return response['payload']
        except Exception as e:
            self.disconnect()
            return f"Error executing command: {str(e)}"

    def _send(self, packet_type: int, payload: str) -> None:
        """Send a low-level RCON packet with a specific type and text payload."""
        self.request_id += 1
        data = struct.pack('<ii', 10+len(payload), self.request_id) + \
               struct.pack('<i', packet_type) + \
               payload.encode('utf-8') + b'\x00\x00'
        self.socket.send(data)

    def _receive(self) -> dict:
        """Receive a single RCON response packet and return its parsed fields."""
        response = self.socket.recv(4096)
        length = struct.unpack('<i', response[:4])[0]
        request_id = struct.unpack('<i', response[4:8])[0]
        packet_type = struct.unpack('<i', response[8:12])[0]
        payload = response[12:-2].decode('utf-8')
        
        return {
            'length': length,
            'request_id': request_id,
            'packet_type': packet_type,
            'payload': payload
        }

class WhitelistView(View):
    """
    Discord UI view that shows buttons to manage the Minecraft whitelist.

    Each button (Add, Remove, List) opens a small workflow to add or remove a
    player, or to show the current list of whitelisted players.
    """
    def __init__(self, rcon, server_type="main"):
        super().__init__(timeout=180)
        self.rcon = rcon
        self.server_type = server_type
    
    @discord.ui.button(label="Add", style=discord.ButtonStyle.green)
    async def add_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        modal = UsernameModal(
            title="Add Player to Whitelist", 
            action="add", 
            rcon=self.rcon,
            server_type=self.server_type
        )
        await interaction.response.send_modal(modal)
    
    @discord.ui.button(label="Remove", style=discord.ButtonStyle.red)
    async def remove_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        modal = UsernameModal(
            title="Remove Player from Whitelist", 
            action="remove", 
            rcon=self.rcon,
            server_type=self.server_type
        )
        await interaction.response.send_modal(modal)
    
    @discord.ui.button(label="List", style=discord.ButtonStyle.blurple)
    async def list_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer(ephemeral=True)
        
        if self.server_type == "klokrise":
            command = "easywl list"
        else:
            command = "whitelist list"
        
        response = self.rcon.send_command(command)
        
        if "There are no whitelisted players" in response or "There are no players on the whitelist" in response:
            formatted_players = "There are no players on the whitelist."
        else:
            try:
                players_part = response.split(": ", 1)[1]
                players_list = [player.strip() for player in players_part.split(",")]
                
                # Improved formatting cleanup for KlokRise server
                if self.server_type == "klokrise":
                    clean_players = []
                    for player in players_list:
                        # Remove all Minecraft color and formatting codes
                        clean_player = re.sub(r'\$[0-9a-f]', '', player)  # Remove basic color codes
                        clean_player = re.sub(r'\$[k-or]', '', clean_player)  # Remove formatting codes
                        clean_player = clean_player.replace('$', '')  # Remove remaining $ characters
                        clean_players.append(clean_player)
                    players_list = clean_players
                
                formatted_players = "\n".join(players_list)
            except (IndexError, ValueError):
                formatted_players = response
        
        embed = discord.Embed(
            title="Whitelisted Players",
            description=formatted_players,
            color=discord.Color.blue()
        )
        
        await interaction.followup.send(embed=embed, ephemeral=True)

class UsernameModal(Modal):
    """
    Simple text input pop-up that asks for a Minecraft username.

    Depending on the chosen action, the bot will add or remove this username
    from the whitelist of the selected Minecraft server.
    """
    def __init__(self, title: str, action: str, rcon, server_type):
        super().__init__(title=title)
        self.action = action
        self.rcon = rcon
        self.server_type = server_type
        
        self.username = TextInput(
            label="Minecraft Username",
            placeholder="Enter a username",
            required=True,
            min_length=3,
            max_length=16
        )
        self.add_item(self.username)
    
    async def on_submit(self, interaction: discord.Interaction):
        username = self.username.value
        await interaction.response.defer(ephemeral=True)
        
        if self.server_type == "klokrise":
            command_prefix = "easywl"
        else:
            command_prefix = "whitelist"
        
        if self.action == "add":
            response = self.rcon.send_command(f"{command_prefix} add {username}")
            color = discord.Color.green()
            title = "Player Added"
        else:
            response = self.rcon.send_command(f"{command_prefix} remove {username}")
            color = discord.Color.red()
            title = "Player Removed"
        
        embed = discord.Embed(
            title=title,
            description=response,
            color=color
        )
        
        await interaction.followup.send(embed=embed, ephemeral=True)

class MyBot(commands.Bot):
    """
    Main Discord bot class that wires together all events and commands.

    It configures the necessary Discord intents, sets the activity text,
    and implements logic for leveling, moderation and role management.
    """
    def __init__(self):
        intents = discord.Intents.default()
        intents.messages = True
        intents.guilds = True
        intents.members = True
        intents.message_content = True
        
        super().__init__(
            command_prefix=COMMAND_PREFIX,
            intents=intents,
            activity=discord.Activity(
                type={
                    "playing": discord.ActivityType.playing,
                    "streaming": discord.ActivityType.streaming,
                    "listening": discord.ActivityType.listening,
                    "watching": discord.ActivityType.watching,
                    "competing": discord.ActivityType.competing,
                }.get(ACTIVITY_TYPE_NAME, discord.ActivityType.watching),
                name=ACTIVITY_TEXT
            )
        )
        self._ready_once = False
        # Removed: self.tree = app_commands.CommandTree(self)
        # The commands.Bot class already initializes self.tree

    async def on_ready(self):
        if self._ready_once:
            print(f"Logged in again as {self.user}")
            return
        self._ready_once = True
        print(f"Logged in as {self.user}")
        try:
            # Use self.tree directly as it's already initialized by commands.Bot
            synced = await self.tree.sync()
            print(f"Synced {len(synced)} commands.")
            await self.check_existing_roles()
        except Exception as e:
            print(f"Sync error: {e}")
    
    async def check_existing_roles(self):
        """Check and fix level-based role assignments for all members in all guilds."""
        for guild in self.guilds:
            print(f"Checking roles in {guild.name}")
            for member in guild.members:
                if member.bot:
                    continue
                    
                user_id = str(member.id)
                if user_id in levels:
                    current_level = levels[user_id]["level"]
                    await self.ensure_correct_roles(member, current_level)
    
    async def ensure_correct_roles(self, member: discord.Member, current_level: int):
        guild = member.guild
        if LEVEL_ROLES:
            max_role_level = max(LEVEL_ROLES.keys())
            effective_level = max_role_level if current_level >= max_role_level else current_level
        else:
            effective_level = current_level
        correct_role_id = LEVEL_ROLES.get(effective_level)
        correct_role = guild.get_role(correct_role_id) if correct_role_id else None
        if correct_role is None and get_auto_create_level_roles():
            role_name = f"Level {effective_level}"
            existing = discord.utils.get(guild.roles, name=role_name)
            if existing is None:
                try:
                    existing = await guild.create_role(name=role_name, reason="Auto-created level role")
                except Exception:
                    existing = None
            if existing is not None:
                set_level_role_mapping(effective_level, existing.id)
                correct_role = existing
                correct_role_id = existing.id
        has_correct_role = bool(correct_role_id and any(role.id == correct_role_id for role in member.roles))
        roles_to_remove = []
        for level, role_id in LEVEL_ROLES.items():
            role = guild.get_role(role_id)
            if role and role in member.roles and level != effective_level:
                roles_to_remove.append(role)
        if not has_correct_role and correct_role_id:
            correct_role = guild.get_role(correct_role_id)
            if correct_role:
                await member.add_roles(correct_role)
                print(f"Added level {current_level} role to {member.display_name}")
        if roles_to_remove:
            await member.remove_roles(*roles_to_remove)
            print(f"Removed {len(roles_to_remove)} incorrect roles from {member.display_name}")

    async def on_member_join(self, member: discord.Member):
        user_id = str(member.id)
        if user_id not in levels:
            levels[user_id] = {
                "level": 0,
                "unique_count": 0,
                "recent_hashes": [],
                "last_message_time": 0,
                "join_date": int(time.time()),
                "violations": {}
            }
            save_levels()
        else:
            current_level = levels[user_id]["level"]
            await self.ensure_correct_roles(member, current_level)

    async def on_message(self, message: discord.Message):
        """
        Handle every message sent in the server.

        This function first checks moderation rules, then updates the leveling
        progress for the author, and finally saves the results to disk.
        """
        if message.author.bot:
            return

        user_id = str(message.author.id)
        now = time.time()

        if user_id not in levels:
            join_date = message.author.joined_at.timestamp() if message.author.joined_at else now
            levels[user_id] = {
                "level": 0,
                "unique_count": 0,
                "recent_hashes": [],
                "last_message_time": 0,
                "join_date": int(join_date),
                "violations": {}
            }
        else:
            ensure_user_schema(user_id)

        content = message.content.strip()
        if not content:
            return

        if await self.handle_moderation(message, content):
            return

        last_time = levels[user_id].get("last_message_time", 0)
        if now - last_time < MESSAGE_COOLDOWN_SECONDS:
            return

        content_hash = message_hash(content)
        recent_hashes = levels[user_id].get("recent_hashes", [])
        if content_hash in recent_hashes:
            return

        recent_hashes.append(content_hash)
        if len(recent_hashes) > RECENT_MESSAGE_HASHES:
            recent_hashes = recent_hashes[-RECENT_MESSAGE_HASHES:]
        levels[user_id]["recent_hashes"] = recent_hashes
        levels[user_id]["unique_count"] = levels[user_id].get("unique_count", 0) + 1
        levels[user_id]["last_message_time"] = int(now)

        current_level = levels[user_id]["level"]
        total_uniques = levels[user_id].get("unique_count", 0)
        next_level = current_level + 1
        leveled_up = False
        
        # Get membership duration
        join_timestamp = levels[user_id].get("join_date", now)
        account_age = now - join_timestamp

        while total_uniques >= required_uniques_for_level(next_level):
            if next_level == 4 and account_age < LEVEL4_MIN_DAYS * 86400:
                break
            if next_level == 5 and account_age < LEVEL5_MIN_DAYS * 86400:
                break
                
            current_level = next_level
            next_level += 1
            leveled_up = True

        if leveled_up:
            levels[user_id]["level"] = current_level
            await message.channel.send(f"🎉 {message.author.mention} has reached level {current_level}!")
            await self.ensure_correct_roles(message.author, current_level)

        save_levels()

    async def handle_moderation(self, message: discord.Message, content: str) -> bool:
        """
        Check a message against the configured moderation rules.

        Returns True if the message triggered moderation (for instance a
        warning or timeout), or False if the message is allowed to stay.
        """
        lowered = content.lower()
        user_id = str(message.author.id)
        if user_id not in levels:
            return False

        directed = bool(message.mentions)
        if not directed:
            for keyword in DIRECT_ADDRESS_KEYWORDS:
                if keyword in f" {lowered} ":
                    directed = True
                    break
        try:
            matched_category_name = None
            matched_category = None
            for category_name, category_config in MODERATION_CATEGORIES.items():
                words = category_config.get("words", [])
                if not words:
                    continue
                require_direct = False
                case_sensitive = bool(category_config.get("case_sensitive", False))
                target_text = content if case_sensitive else lowered
                for word in words:
                    word_str = str(word)
                    if not case_sensitive:
                        word_str = word_str.lower()
                    if not word_str:
                        continue
                    pattern = rf"\b{re.escape(word_str)}\b"
                    if re.search(pattern, target_text):
                        matched_category_name = category_name
                        matched_category = category_config
                        break
                if matched_category:
                    break

            if not matched_category_name:
                return False

            delete_message = bool(matched_category.get("delete_message", True))
            max_violations = int(matched_category.get("max_violations", 1))
            timeout_days = float(matched_category.get("timeout_days", 1))
            dm_on_timeout = bool(matched_category.get("dm_on_timeout", True))

            ensure_user_schema(user_id)
            violations_data = levels[user_id].get("violations")
            if not isinstance(violations_data, dict):
                violations_data = {}
            previous_violations = int(violations_data.get(matched_category_name, 0))
            current_violations = previous_violations + 1
            violations_data[matched_category_name] = current_violations
            levels[user_id]["violations"] = violations_data

            display_violations = current_violations
            if max_violations > 0:
                display_violations = min(current_violations, max_violations)

            if delete_message:
                try:
                    await message.delete()
                except discord.Forbidden:
                    pass
                except discord.HTTPException:
                    pass

            warning_sent = False
            send_warning = False
            if PUBLIC_WARNING_ENABLED:
                if max_violations > 0:
                    if previous_violations < max_violations:
                        send_warning = True
                else:
                    send_warning = True

            if send_warning:
                try:
                    warning_text = PUBLIC_WARNING_TEMPLATE.format(
                        user=message.author.mention,
                        category=matched_category_name,
                        count=display_violations,
                        max=max_violations,
                    )
                    await message.channel.send(warning_text, delete_after=20)
                    warning_sent = True
                except discord.Forbidden:
                    warning_sent = False
                except discord.HTTPException:
                    warning_sent = False

            if VIOLATION_DM_ENABLED:
                try:
                    excerpt = content[:200]
                    dm_text = VIOLATION_DM_TEMPLATE.format(
                        user=message.author.mention,
                        category=matched_category_name,
                        count=current_violations,
                        max=max_violations,
                        message=excerpt,
                    )
                    await message.author.send(dm_text)
                except discord.Forbidden:
                    pass
                except discord.HTTPException:
                    pass

            if STAFF_LOG_CHANNEL_ID:
                staff_channel = message.guild.get_channel(STAFF_LOG_CHANNEL_ID)
                if staff_channel:
                    try:
                        excerpt = content[:200]
                        log_text = STAFF_LOG_TEMPLATE.format(
                            user=message.author.mention,
                            channel=message.channel.mention,
                            category=matched_category_name,
                            count=current_violations,
                            max=max_violations,
                            message=excerpt,
                        )
                        await staff_channel.send(log_text)
                    except discord.Forbidden:
                        pass
                    except discord.HTTPException:
                        pass

            punishment_cfg = matched_category.get("violation_punishments")
            punishment_info = None
            if isinstance(punishment_cfg, dict) and punishment_cfg:
                raw = punishment_cfg.get(str(current_violations))
                if raw is None:
                    best_key = None
                    for k in punishment_cfg.keys():
                        try:
                            n = int(k)
                        except (TypeError, ValueError):
                            continue
                        if n <= current_violations and (best_key is None or n > best_key):
                            best_key = n
                    if best_key is not None:
                        raw = punishment_cfg.get(str(best_key))
                if isinstance(raw, str):
                    punishment_info = {"type": raw.strip().lower()}
                elif isinstance(raw, dict):
                    ptype = raw.get("type")
                    if isinstance(ptype, str):
                        ptype = ptype.strip().lower()
                        info = {"type": ptype}
                        duration_value = raw.get("duration_seconds")
                        if isinstance(duration_value, (int, float)) and duration_value > 0:
                            info["duration_seconds"] = int(duration_value)
                        punishment_info = info
            else:
                if (
                    max_violations > 0
                    and timeout_days > 0
                    and current_violations >= max_violations
                ):
                    seconds = int(timeout_days * 24 * 60 * 60)
                    if seconds <= 0:
                        seconds = 60
                    punishment_info = {
                        "type": "timeout",
                        "duration_seconds": seconds,
                    }

            if isinstance(punishment_info, dict):
                ptype = punishment_info.get("type")
                if isinstance(ptype, str):
                    ptype = ptype.strip().lower()
                else:
                    ptype = None
                if ptype and ptype not in ("none", "off"):
                    guild = message.guild
                    member = message.author
                    if guild is not None and isinstance(member, discord.Member):
                        try:
                            if ptype == "timeout":
                                total_seconds = punishment_info.get("duration_seconds")
                                if not isinstance(total_seconds, int) or total_seconds <= 0:
                                    total_seconds = int(timeout_days * 24 * 60 * 60)
                                    if total_seconds <= 0:
                                        total_seconds = 60
                                until = utcnow() + timedelta(seconds=total_seconds)
                                await member.timeout(
                                    until,
                                    reason=f"Automatic timeout for {matched_category_name} violation {current_violations}",
                                )
                                seconds_value = int(total_seconds)
                                if seconds_value % 86400 == 0:
                                    days = seconds_value // 86400
                                    unit = "day" if days == 1 else "days"
                                    duration_text = f"{days} {unit}"
                                elif seconds_value % 3600 == 0:
                                    hours = seconds_value // 3600
                                    unit = "hour" if hours == 1 else "hours"
                                    duration_text = f"{hours} {unit}"
                                elif seconds_value % 60 == 0:
                                    minutes_value = seconds_value // 60
                                    unit = "minute" if minutes_value == 1 else "minutes"
                                    duration_text = f"{minutes_value} {unit}"
                                else:
                                    duration_text = f"{seconds_value} seconds"
                                if dm_on_timeout:
                                    description = (
                                        f"You have received a timeout in {guild.name}.\n"
                                        f"Duration: {duration_text}\n"
                                        f"Reason: Automatic punishment for {matched_category_name} violation {current_violations}\n"
                                    )
                                    await send_punishment_dm(
                                        member,
                                        guild,
                                        "Timeout",
                                        description,
                                    )
                                log_punishment(
                                    guild.id,
                                    member.id,
                                    "timeout_set",
                                    {
                                        "duration_seconds": total_seconds,
                                        "reason": f"Automatic punishment for {matched_category_name} violation {current_violations}",
                                        "automatic": True,
                                    },
                                )
                                asyncio.create_task(
                                    schedule_timeout_end(
                                        guild.id,
                                        member.id,
                                        total_seconds,
                                    )
                                )
                            elif ptype == "mute":
                                muted_role = await ensure_muted_role(guild)
                                if muted_role is not None and muted_role not in member.roles:
                                    await member.add_roles(
                                        muted_role,
                                        reason=f"Automatic mute for {matched_category_name} violation {current_violations}",
                                    )
                                    total_seconds = punishment_info.get("duration_seconds")
                                    duration_text = None
                                    if isinstance(total_seconds, (int, float)) and total_seconds > 0:
                                        total_seconds = int(total_seconds)
                                        if total_seconds % 86400 == 0:
                                            days = total_seconds // 86400
                                            unit = "day" if days == 1 else "days"
                                            duration_text = f"{days} {unit}"
                                        elif total_seconds % 3600 == 0:
                                            hours = total_seconds // 3600
                                            unit = "hour" if hours == 1 else "hours"
                                            duration_text = f"{hours} {unit}"
                                        elif total_seconds % 60 == 0:
                                            minutes_value = total_seconds // 60
                                            unit = "minute" if minutes_value == 1 else "minutes"
                                            duration_text = f"{minutes_value} {unit}"
                                        else:
                                            duration_text = f"{total_seconds} seconds"
                                    description_parts = [
                                        f"You have been muted in {guild.name}.",
                                    ]
                                    if duration_text:
                                        description_parts.append(f"Duration: {duration_text}")
                                    description_parts.append(
                                        f"Reason: Automatic punishment for {matched_category_name} violation {current_violations}"
                                    )
                                    description = "\n".join(description_parts) + "\n"
                                    await send_punishment_dm(
                                        member,
                                        guild,
                                        "Mute",
                                        description,
                                    )
                                    log_info = {
                                        "reason": f"Automatic punishment for {matched_category_name} violation {current_violations}",
                                        "automatic": True,
                                    }
                                    if isinstance(total_seconds, int) and total_seconds > 0:
                                        log_info["duration_seconds"] = total_seconds
                                        asyncio.create_task(
                                            schedule_unmute(
                                                guild.id,
                                                member.id,
                                                total_seconds,
                                            )
                                        )
                                    log_punishment(
                                        guild.id,
                                        member.id,
                                        "mute_set",
                                        log_info,
                                    )
                            elif ptype == "ban":
                                reason_text = (
                                    f"Automatic ban for {matched_category_name} violation {current_violations}"
                                )
                                await guild.ban(member, reason=reason_text)
                                description = (
                                    f"You have been banned from {guild.name}.\n"
                                    f"Reason: {reason_text}\n"
                                )
                                await send_punishment_dm(
                                    member,
                                    guild,
                                    "Ban",
                                    description,
                                )
                                log_punishment(
                                    guild.id,
                                    member.id,
                                    "ban_set",
                                    {
                                        "reason": reason_text,
                                        "automatic": True,
                                    },
                                )
                            elif ptype == "kick":
                                reason_text = (
                                    f"Automatic kick for {matched_category_name} violation {current_violations}"
                                )
                                await guild.kick(member, reason=reason_text)
                                description = (
                                    f"You have been kicked from {guild.name}.\n"
                                    f"Reason: {reason_text}\n"
                                )
                                await send_punishment_dm(
                                    member,
                                    guild,
                                    "Kick",
                                    description,
                                )
                                log_punishment(
                                    guild.id,
                                    member.id,
                                    "kick",
                                    {
                                        "reason": reason_text,
                                        "automatic": True,
                                    },
                                )
                        except discord.Forbidden:
                            pass
                        except Exception:
                            pass

            try:
                category_level_penalty = matched_category.get("level_penalty")
                penalty_value = 0
                if isinstance(category_level_penalty, (int, float)):
                    penalty_value = int(category_level_penalty)
                elif isinstance(category_level_penalty, str) and category_level_penalty.strip():
                    try:
                        penalty_value = int(category_level_penalty.strip())
                    except ValueError:
                        penalty_value = 0
                level_reset_to_cfg = matched_category.get("level_reset_to")
                reset_level_value = None
                if isinstance(level_reset_to_cfg, (int, float)):
                    reset_level_value = int(level_reset_to_cfg)
                elif isinstance(level_reset_to_cfg, str) and level_reset_to_cfg.strip():
                    try:
                        reset_level_value = int(level_reset_to_cfg.strip())
                    except ValueError:
                        reset_level_value = None
                if penalty_value > 0 or (reset_level_value is not None and reset_level_value > 0):
                    user_data = levels.get(user_id)
                    if isinstance(user_data, dict):
                        current_level_value = int(user_data.get("level", 0))
                        new_level_value = current_level_value
                        if penalty_value > 0:
                            new_level_value = max(0, new_level_value - penalty_value)
                        if reset_level_value is not None and reset_level_value > 0:
                            if new_level_value > reset_level_value:
                                new_level_value = reset_level_value
                        if new_level_value != current_level_value:
                            user_data["level"] = new_level_value
                            if isinstance(message.author, discord.Member):
                                await self.ensure_correct_roles(message.author, new_level_value)
            except Exception:
                pass

            save_levels()
            return True
        except Exception:
            return False

bot = MyBot()

class ModerationSettingsModal(Modal):
    def __init__(self, category_name: str, view: "ModerationConfigView"):
        super().__init__(title=f"Basic settings for {category_name}")
        self.category_name = category_name
        self.view = view

        self.max_violations = TextInput(
            label="How many warnings before punishment?",
            placeholder="Leave empty to keep current value",
            required=False,
        )
        self.timeout_days = TextInput(
            label="Timeout length in days (0 = no timeout)",
            placeholder="Leave empty to keep current value",
            required=False,
        )
        self.require_direct_address = TextInput(
            label="Only punish if message is aimed at someone? (yes/no)",
            placeholder="Type yes or no, empty = keep current value",
            required=False,
        )
        self.delete_message = TextInput(
            label="Delete the offending message? (yes/no)",
            placeholder="Type yes or no, empty = keep current value",
            required=False,
        )
        self.case_sensitive = TextInput(
            label="Match words exactly (case-sensitive)? (yes/no)",
            placeholder="Type yes or no, empty = keep current value",
            required=False,
        )

        self.add_item(self.max_violations)
        self.add_item(self.timeout_days)
        self.add_item(self.require_direct_address)
        self.add_item(self.delete_message)
        self.add_item(self.case_sensitive)

    async def on_submit(self, interaction: discord.Interaction):
        category_cfg = MODERATION_CATEGORIES.get(self.category_name)
        if not isinstance(category_cfg, dict):
            await interaction.response.send_message(
                "Category not found.", ephemeral=True
            )
            return

        def parse_bool(value: str) -> bool | None:
            lowered_value = value.strip().lower()
            if lowered_value in ("true", "1", "ja", "yes"):
                return True
            if lowered_value in ("false", "0", "nee", "no"):
                return False
            return None

        if self.max_violations.value.strip():
            try:
                mv = int(self.max_violations.value.strip())
                if mv < 0:
                    mv = 0
                category_cfg["max_violations"] = mv
            except ValueError:
                pass

        if self.timeout_days.value.strip():
            try:
                td = float(self.timeout_days.value.strip())
                if td < 0:
                    td = 0
                category_cfg["timeout_days"] = td
            except ValueError:
                pass

        if self.require_direct_address.value.strip():
            parsed = parse_bool(self.require_direct_address.value)
            if parsed is not None:
                category_cfg["require_direct_address"] = parsed

        if self.delete_message.value.strip():
            parsed = parse_bool(self.delete_message.value)
            if parsed is not None:
                category_cfg["delete_message"] = parsed

        if self.case_sensitive.value.strip():
            parsed = parse_bool(self.case_sensitive.value)
            if parsed is not None:
                category_cfg["case_sensitive"] = parsed

        save_config()

        if self.view.message:
            embed = self.view.build_embed(self.category_name)
            await self.view.message.edit(embed=embed, view=self.view)

        await interaction.response.send_message(
            "Settings updated.", ephemeral=True
        )


class ViolationPunishmentsModal(Modal):
    def __init__(self, category_name: str, view: "ModerationConfigView"):
        super().__init__(title=f"Punishments for {category_name}")
        self.category_name = category_name
        self.view = view

        self.second_violation = TextInput(
            label="2nd violation punishment",
            placeholder="Describe the punishment for a second violation",
            required=False,
        )
        self.third_violation = TextInput(
            label="3rd violation punishment",
            placeholder="Leave empty to keep current value",
            required=False,
        )
        self.fourth_violation = TextInput(
            label="4th violation punishment",
            placeholder="Leave empty to keep current value",
            required=False,
        )
        self.fifth_violation = TextInput(
            label="5th violation punishment",
            placeholder="Leave empty to keep current value",
            required=False,
        )

        self.add_item(self.second_violation)
        self.add_item(self.third_violation)
        self.add_item(self.fourth_violation)
        self.add_item(self.fifth_violation)

    async def on_submit(self, interaction: discord.Interaction):
        category_cfg = MODERATION_CATEGORIES.get(self.category_name)
        if not isinstance(category_cfg, dict):
            await interaction.response.send_message(
                "Category not found.", ephemeral=True
            )
            return

        punishments_cfg = category_cfg.get("violation_punishments")
        if not isinstance(punishments_cfg, dict):
            punishments_cfg = {}

        def parse_input(value: str) -> dict | None | str:
            text = value.strip()
            if not text:
                return None
            lowered = text.lower()
            if lowered in ("none", "geen", "off", "uit"):
                return "none"
            parts = lowered.split()
            if not parts:
                return None
            ptype = parts[0]
            duration_seconds = None
            if len(parts) >= 3:
                try:
                    amount = int(parts[1])
                except ValueError:
                    amount = None
                unit_raw = parts[2]
                unit_map = {
                    "s": "seconds",
                    "sec": "seconds",
                    "secs": "seconds",
                    "second": "seconds",
                    "seconds": "seconds",
                    "m": "minutes",
                    "min": "minutes",
                    "mins": "minutes",
                    "minute": "minutes",
                    "minutes": "minutes",
                    "h": "hours",
                    "hr": "hours",
                    "hrs": "hours",
                    "hour": "hours",
                    "hours": "hours",
                    "d": "days",
                    "day": "days",
                    "days": "days",
                    "w": "weeks",
                    "week": "weeks",
                    "weeks": "weeks",
                    "mo": "months",
                    "month": "months",
                    "months": "months",
                    "y": "years",
                    "yr": "years",
                    "year": "years",
                    "years": "years",
                }
                unit_key = unit_map.get(unit_raw)
                if amount is not None and unit_key in UNIT_TO_SECONDS:
                    duration_seconds = amount * UNIT_TO_SECONDS[unit_key]
            result: dict[str, object] = {"type": ptype}
            if duration_seconds is not None and duration_seconds > 0:
                result["duration_seconds"] = int(duration_seconds)
            return result

        entries = [
            (2, self.second_violation.value),
            (3, self.third_violation.value),
            (4, self.fourth_violation.value),
            (5, self.fifth_violation.value),
        ]

        for number, raw_value in entries:
            if not raw_value.strip():
                continue
            parsed = parse_input(raw_value)
            key = str(number)
            if parsed is None:
                continue
            if parsed == "none":
                if key in punishments_cfg:
                    punishments_cfg.pop(key, None)
                continue
            if isinstance(parsed, dict):
                punishments_cfg[key] = parsed

        if punishments_cfg:
            category_cfg["violation_punishments"] = punishments_cfg
        elif "violation_punishments" in category_cfg:
            category_cfg.pop("violation_punishments", None)

        save_config()

        if self.view.message:
            embed = self.view.build_embed(self.category_name)
            await self.view.message.edit(embed=embed, view=self.view)

        await interaction.response.send_message(
            "Punishments updated.", ephemeral=True
        )


class LevelPenaltyModal(Modal):
    def __init__(self, category_name: str, view: "ModerationConfigView"):
        super().__init__(title=f"Level penalties for {category_name}")
        self.category_name = category_name
        self.view = view

        self.level_penalty = TextInput(
            label="Levels to subtract per violation (0 = none)",
            placeholder="Number, empty = unchanged",
            required=False,
        )
        self.level_reset_to = TextInput(
            label="Reset level to (optional)",
            placeholder="Number, empty = unchanged / no reset",
            required=False,
        )

        self.add_item(self.level_penalty)
        self.add_item(self.level_reset_to)

    async def on_submit(self, interaction: discord.Interaction):
        category_cfg = MODERATION_CATEGORIES.get(self.category_name)
        if not isinstance(category_cfg, dict):
            await interaction.response.send_message(
                "Category not found.", ephemeral=True
            )
            return

        if self.level_penalty.value.strip():
            try:
                lp = int(self.level_penalty.value.strip())
                if lp < 0:
                    lp = 0
                category_cfg["level_penalty"] = lp
            except ValueError:
                pass

        if self.level_reset_to.value.strip():
            try:
                lr = int(self.level_reset_to.value.strip())
                if lr < 0:
                    lr = 0
                category_cfg["level_reset_to"] = lr
            except ValueError:
                pass

        save_config()

        if self.view.message:
            embed = self.view.build_embed(self.category_name)
            await self.view.message.edit(embed=embed, view=self.view)

        await interaction.response.send_message(
            "Level penalties updated.", ephemeral=True
        )

class ModerationWordsModal(Modal):
    def __init__(self, category_name: str, view: "ModerationConfigView"):
        super().__init__(title=f"Blocked words for {category_name}")
        self.category_name = category_name
        self.view = view
        self.add_words = TextInput(
            label="Add new blocked words",
            placeholder="Separate words with commas",
            required=False,
        )
        self.remove_words = TextInput(
            label="Remove blocked words",
            placeholder="Separate words with commas",
            required=False,
        )

        self.add_item(self.add_words)
        self.add_item(self.remove_words)

    async def on_submit(self, interaction: discord.Interaction):
        category_cfg = MODERATION_CATEGORIES.get(self.category_name)
        if not isinstance(category_cfg, dict):
            await interaction.response.send_message(
                "Category not found.", ephemeral=True
            )
            return
        def parse_words(value: str) -> list[str]:
            parts = [w.strip() for w in value.split(",")]
            return [w for w in parts if w]
        case_sensitive = bool(category_cfg.get("case_sensitive", False))
        def norm(w: str) -> str:
            return w if case_sensitive else w.lower()

        if self.add_words.value.strip():
            new_words = parse_words(self.add_words.value)
            existing_words = category_cfg.get("words", [])
            if not isinstance(existing_words, list):
                existing_words = []
            seen = set()
            result: list[str] = []
            for w in existing_words:
                k = norm(str(w))
                if k not in seen:
                    seen.add(k)
                    result.append(str(w) if case_sensitive else k)
            for word in new_words:
                k = norm(word)
                if k not in seen:
                    seen.add(k)
                    result.append(word if case_sensitive else k)
            category_cfg["words"] = result

        if self.remove_words.value.strip():
            remove_words = set(parse_words(self.remove_words.value))
            existing_words = category_cfg.get("words", [])
            if isinstance(existing_words, list):
                if case_sensitive:
                    category_cfg["words"] = [w for w in existing_words if str(w) not in remove_words]
                else:
                    rem_norm = {norm(w) for w in remove_words}
                    category_cfg["words"] = [str(w).lower() for w in existing_words if norm(str(w)) not in rem_norm]

        save_config()

        if self.view.message:
            embed = self.view.build_embed(self.category_name)
            await self.view.message.edit(embed=embed, view=self.view)

        await interaction.response.send_message(
            "Words updated.", ephemeral=True
        )


class WarningsUserSelect(discord.ui.Select):
    def __init__(
        self,
        invoker: discord.Member,
        guild: discord.Guild,
        allowed_ids: list[int] | None = None,
    ):
        self.invoker_id = invoker.id

        options: list[discord.SelectOption] = []
        for user_id, data in levels.items():
            if not isinstance(data, dict):
                continue
            if allowed_ids is not None and int(user_id) not in allowed_ids:
                continue

            violations_data = data.get("violations", {})
            if not isinstance(violations_data, dict) or not violations_data:
                continue

            member = guild.get_member(int(user_id))
            if not member:
                continue

            total_warnings = 0
            for count in violations_data.values():
                try:
                    total_warnings += int(count)
                except (TypeError, ValueError):
                    continue

            label = f"{member.display_name} ({total_warnings} warnings)"
            description = f"ID: {member.id}"
            options.append(
                discord.SelectOption(
                    label=label[:100],
                    value=str(member.id),
                    description=description[:100],
                )
            )

        if not options:
            options.append(
                discord.SelectOption(
                    label="No users with warnings",
                    value="none",
                    default=True,
                )
            )

        super().__init__(
            placeholder="Select a user to manage warnings",
            min_values=1,
            max_values=1,
            options=options,
        )

    async def callback(self, interaction: discord.Interaction):
        if not has_level_admin_role(interaction.user):
            await interaction.response.send_message(
                "You don't have permission for this.", ephemeral=True
            )
            return
        if interaction.user.id != self.invoker_id:
            await interaction.response.send_message(
                "Only the original requester can use this interface.",
                ephemeral=True,
            )
            return

        if not self.values:
            await interaction.response.send_message(
                "No user selected.", ephemeral=True
            )
            return

        selected = self.values[0]
        if selected == "none":
            await interaction.response.send_message(
                "There are currently no users with recorded warnings.",
                ephemeral=True,
            )
            return

        try:
            user_id = int(selected)
        except ValueError:
            await interaction.response.send_message(
                "Invalid user selection.", ephemeral=True
            )
            return

        member = interaction.guild.get_member(user_id)
        if member is None:
            await interaction.response.send_message(
                "User not found in this server.", ephemeral=True
            )
            return

        user_id_str = str(member.id)
        if user_id_str not in levels:
            await interaction.response.send_message(
                f"No leveling or warning data found for {member.mention}.",
                ephemeral=True,
            )
            return

        ensure_user_schema(user_id_str)
        data = levels[user_id_str]
        violations_data = data.get("violations", {})

        if not isinstance(violations_data, dict) or not violations_data:
            await interaction.response.send_message(
                f"{member.mention} currently has no recorded warnings.",
                ephemeral=True,
            )
            return

        view = UserViolationsView(interaction.user, member)
        embed = view.build_embed()
        await interaction.response.edit_message(embed=embed, view=view)


class WarningsUserModal(Modal):
    def __init__(self, invoker: discord.Member):
        super().__init__(title="Search user warnings")
        self.invoker_id = invoker.id

        self.query = TextInput(
            label="User",
            placeholder="Mention, ID, or name",
            required=True,
        )
        self.add_item(self.query)

    async def on_submit(self, interaction: discord.Interaction):
        if not has_level_admin_role(interaction.user):
            await interaction.response.send_message(
                "You don't have permission for this.", ephemeral=True
            )
            return
        if interaction.user.id != self.invoker_id:
            await interaction.response.send_message(
                "Only the original requester can use this interface.",
                ephemeral=True,
            )
            return

        raw_value = self.query.value.strip()
        if not interaction.guild:
            await interaction.response.send_message(
                "This search can only be used inside a server.",
                ephemeral=True,
            )
            return

        guild = interaction.guild
        candidates: list[discord.Member] = []

        match = re.search(r"(\d{15,20})", raw_value)
        if match:
            try:
                user_id = int(match.group(1))
                member = guild.get_member(user_id)
                if member is not None:
                    candidates.append(member)
            except ValueError:
                pass

        lowered = raw_value.lower()
        for m in guild.members:
            if m in candidates:
                continue
            if lowered in m.display_name.lower() or lowered in m.name.lower():
                candidates.append(m)

        if not candidates:
            await interaction.response.send_message(
                "No users found matching that query.",
                ephemeral=True,
            )
            return

        matching_ids = [m.id for m in candidates[:25]]

        view = WarningsUserSearchResultsView(interaction.user, guild, matching_ids)
        embed = discord.Embed(
            title="Search results",
            description=f"Results for '{raw_value}'. Select a user below.",
            color=discord.Color.orange(),
        )
        await interaction.response.send_message(
            embed=embed, view=view, ephemeral=True
        )


class WarningsSearchButton(discord.ui.Button):
    def __init__(self, invoker: discord.Member):
        self.invoker_id = invoker.id
        super().__init__(
            label="Search user",
            style=discord.ButtonStyle.primary,
            row=1,
        )

    async def callback(self, interaction: discord.Interaction):
        if not has_level_admin_role(interaction.user):
            await interaction.response.send_message(
                "You don't have permission for this.", ephemeral=True
            )
            return
        if interaction.user.id != self.invoker_id:
            await interaction.response.send_message(
                "Only the original requester can use this interface.",
                ephemeral=True,
            )
            return

        modal = WarningsUserModal(interaction.user)
        await interaction.response.send_modal(modal)


class WarningsUserSelectView(View):
    def __init__(self, invoker: discord.Member, guild: discord.Guild):
        super().__init__(timeout=300)
        self.invoker_id = invoker.id
        self.guild = guild
        self.add_item(WarningsUserSelect(invoker, guild))
        self.add_item(WarningsSearchButton(invoker))

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.invoker_id:
            await interaction.response.send_message(
                "Only the original requester can use this interface.",
                ephemeral=True,
            )
            return False
        return True


class WarningsUserSearchResultsView(View):
    def __init__(
        self,
        invoker: discord.Member,
        guild: discord.Guild,
        allowed_ids: list[int],
    ):
        super().__init__(timeout=300)
        self.invoker_id = invoker.id
        self.guild = guild
        self.add_item(WarningsUserSelect(invoker, guild, allowed_ids))

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.invoker_id:
            await interaction.response.send_message(
                "Only the original requester can use this interface.",
                ephemeral=True,
            )
            return False
        return True

class DirectAddressKeywordsModal(Modal):
    def __init__(self, view: "ModerationConfigView"):
        super().__init__(title="Direct address keywords")
        self.view = view

        self.add_words = TextInput(
            label="Add keywords (comma-separated)",
            placeholder="Comma-separated list of keywords",
            required=False,
        )
        self.remove_words = TextInput(
            label="Remove keywords (comma-separated)",
            placeholder="optional: keywords to remove",
            required=False,
        )

        self.add_item(self.add_words)
        self.add_item(self.remove_words)

    async def on_submit(self, interaction: discord.Interaction):
        global DIRECT_ADDRESS_KEYWORDS

        moderation_cfg = CONFIG.get("moderation", MODERATION_CONFIG)
        current_keywords = moderation_cfg.get("direct_address_keywords", DIRECT_ADDRESS_KEYWORDS)
        if not isinstance(current_keywords, list):
            current_keywords = []

        keywords = [str(w) for w in current_keywords]

        if self.add_words.value.strip():
            new_words = [
                w.strip()
                for w in self.add_words.value.split(",")
                if w.strip()
            ]
            for word in new_words:
                if word not in keywords:
                    keywords.append(word)

        if self.remove_words.value.strip():
            remove_list = [
                w.strip()
                for w in self.remove_words.value.split(",")
                if w.strip()
            ]
            keywords = [w for w in keywords if w not in remove_list]

        moderation_cfg["direct_address_keywords"] = keywords
        CONFIG["moderation"] = moderation_cfg
        DIRECT_ADDRESS_KEYWORDS = keywords

        save_config()

        if self.view.message:
            embed = self.view.build_embed(self.view.current_category)
            await self.view.message.edit(embed=embed, view=self.view)

        await interaction.response.send_message(
            "Direct address keywords updated.", ephemeral=True
        )

class ModerationCategorySelect(discord.ui.Select):
    def __init__(self, view: "ModerationConfigView"):
        self.view_ref = view
        options = []
        for name in MODERATION_CATEGORIES.keys():
            options.append(
                discord.SelectOption(
                    label=name,
                    value=name,
                    default=name == view.current_category,
                )
            )
        super().__init__(
            placeholder="Choose a category",
            min_values=1,
            max_values=1,
            options=options,
        )

    async def callback(self, interaction: discord.Interaction):
        if not has_level_admin_role(interaction.user):
            await interaction.response.send_message(
                "You don't have permission for this.", ephemeral=True
            )
            return

        selected = self.values[0]
        self.view_ref.current_category = selected
        for option in self.options:
            option.default = option.value == selected
        embed = self.view_ref.build_embed(selected)
        await interaction.response.edit_message(embed=embed, view=self.view_ref)

class ModerationConfigView(View):
    def __init__(self, invoker: discord.Member):
        super().__init__(timeout=300)
        self.invoker_id = invoker.id
        self.current_category = next(iter(MODERATION_CATEGORIES.keys()))
        self.message: discord.Message | None = None
        self.add_item(ModerationCategorySelect(self))

    def build_embed(self, category_name: str) -> discord.Embed:
        category_cfg = MODERATION_CATEGORIES.get(category_name, {})
        words = category_cfg.get("words", [])
        max_violations = int(category_cfg.get("max_violations", 1))
        timeout_days = float(category_cfg.get("timeout_days", 0))
        require_direct = bool(category_cfg.get("require_direct_address", False))
        delete_message = bool(category_cfg.get("delete_message", True))
        dm_on_timeout = bool(category_cfg.get("dm_on_timeout", True))
        case_sensitive = bool(category_cfg.get("case_sensitive", False))
        direct_keywords = CONFIG.get("moderation", {}).get(
            "direct_address_keywords", DIRECT_ADDRESS_KEYWORDS
        )
        if not isinstance(direct_keywords, list):
            direct_keywords = []

        def norm(w: str) -> str:
            return w if case_sensitive else str(w).lower()
        if isinstance(words, list):
            seen = set()
            unique_words: list[str] = []
            for w in words:
                k = norm(str(w))
                if k not in seen:
                    seen.add(k)
                    unique_words.append(str(w) if case_sensitive else k)
            words = unique_words

        description_lines = [
            f"Max violations: {max_violations}",
            f"Timeout: {timeout_days} days" if timeout_days > 0 else "Timeout: off",
            f"Only on direct address: {'yes' if require_direct else 'no'}",
            f"Delete message: {'yes' if delete_message else 'no'}",
            f"DM on timeout: {'yes' if dm_on_timeout else 'no'}",
            f"Case sensitive: {'yes' if case_sensitive else 'no'}",
            "",
            f"Blocked words ({len(words)}):",
        ]

        if words:
            description_lines.append(", ".join(str(w) for w in words))
        else:
            description_lines.append("No words configured.")

        description_lines.append("")
        punish_cfg = category_cfg.get("violation_punishments")
        punish_text_lines: list[str] = []
        if isinstance(punish_cfg, dict) and punish_cfg:
            for n in range(2, 6):
                key = str(n)
                value = punish_cfg.get(key)
                if value is None:
                    continue
                if isinstance(value, str):
                    ptype = value.strip().lower()
                    pdata = {"type": ptype}
                elif isinstance(value, dict):
                    pdata = value
                    ptype = str(pdata.get("type", "")).strip().lower()
                else:
                    continue
                if not ptype or ptype in ("none", "off"):
                    text = "none"
                else:
                    label = ptype.capitalize()
                    duration_seconds = pdata.get("duration_seconds")
                    if isinstance(duration_seconds, (int, float)) and duration_seconds > 0:
                        seconds_value = int(duration_seconds)
                        if seconds_value % 86400 == 0:
                            days = seconds_value // 86400
                            unit = "day" if days == 1 else "days"
                            dur_text = f"{days} {unit}"
                        elif seconds_value % 3600 == 0:
                            hours = seconds_value // 3600
                            unit = "hour" if hours == 1 else "hours"
                            dur_text = f"{hours} {unit}"
                        elif seconds_value % 60 == 0:
                            minutes_value = seconds_value // 60
                            unit = "minute" if minutes_value == 1 else "minutes"
                            dur_text = f"{minutes_value} {unit}"
                        else:
                            dur_text = f"{seconds_value} seconds"
                        text = f"{label} ({dur_text})"
                    else:
                        text = label
                if n == 2:
                    label = "2nd violation"
                elif n == 3:
                    label = "3rd violation"
                elif n == 4:
                    label = "4th violation"
                else:
                    label = "5th violation"
                punish_text_lines.append(f"{label}: {text}")
        if punish_text_lines:
            description_lines.append("Punishments:")
            description_lines.extend(punish_text_lines)
            description_lines.append("")
        level_penalty = category_cfg.get("level_penalty", 0)
        level_reset_to = category_cfg.get("level_reset_to")
        lp_value = 0
        if isinstance(level_penalty, (int, float)):
            lp_value = int(level_penalty)
        elif isinstance(level_penalty, str) and level_penalty.strip():
            try:
                lp_value = int(level_penalty.strip())
            except ValueError:
                lp_value = 0
        lr_value = None
        if isinstance(level_reset_to, (int, float)):
            lr_value = int(level_reset_to)
        elif isinstance(level_reset_to, str) and level_reset_to.strip():
            try:
                lr_value = int(level_reset_to.strip())
            except ValueError:
                lr_value = None

        description_lines.append("Level penalties:")
        description_lines.append(
            f"- Levels to subtract per violation: {lp_value}"
        )
        if lr_value is not None and lr_value > 0:
            description_lines.append(f"- Reset level to: {lr_value}")
        else:
            description_lines.append("- Reset level to: none")
        description_lines.append("")
        description_lines.append(
            f"Direct address keywords ({len(direct_keywords)}):"
        )
        if direct_keywords:
            description_lines.append(", ".join(str(w) for w in direct_keywords))
        else:
            description_lines.append("No direct address keywords configured.")

        embed = discord.Embed(
            title=f"Moderation category: {category_name}",
            color=discord.Color.purple(),
            description="\n".join(description_lines),
        )
        return embed

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if not has_level_admin_role(interaction.user):
            await interaction.response.send_message(
                "You don't have permission for this.", ephemeral=True
            )
            return False
        return True

    @discord.ui.button(
        label="Edit settings",
        style=discord.ButtonStyle.primary,
        row=1,
    )
    async def settings_button(
        self, interaction: discord.Interaction, button: Button
    ):
        modal = ModerationSettingsModal(self.current_category, self)
        await interaction.response.send_modal(modal)

    @discord.ui.button(
        label="Manage words",
        style=discord.ButtonStyle.secondary,
        row=1,
    )
    async def words_button(
        self, interaction: discord.Interaction, button: Button
    ):
        modal = ModerationWordsModal(self.current_category, self)
        await interaction.response.send_modal(modal)

    @discord.ui.button(
        label="Direct address keywords",
        style=discord.ButtonStyle.secondary,
        row=2,
    )
    async def direct_address_button(
        self, interaction: discord.Interaction, button: Button
    ):
        modal = DirectAddressKeywordsModal(self)
        await interaction.response.send_modal(modal)

    @discord.ui.button(
        label="Level penalties",
        style=discord.ButtonStyle.secondary,
        row=2,
    )
    async def level_penalties_button(
        self, interaction: discord.Interaction, button: Button
    ):
        modal = LevelPenaltyModal(self.current_category, self)
        await interaction.response.send_modal(modal)

    @discord.ui.button(
        label="Punishments",
        style=discord.ButtonStyle.secondary,
        row=2,
    )
    async def punishments_button(
        self, interaction: discord.Interaction, button: Button
    ):
        modal = ViolationPunishmentsModal(self.current_category, self)
        await interaction.response.send_modal(modal)

    @discord.ui.button(
        label="Close",
        style=discord.ButtonStyle.danger,
        row=2,
    )
    async def close_button(
        self, interaction: discord.Interaction, button: Button
    ):
        await interaction.response.defer(ephemeral=True, thinking=False)
        for child in self.children:
            child.disabled = True
        if self.message:
            await self.message.edit(view=self)
class UserViolationsCategorySelect(discord.ui.Select):
    def __init__(self, view: "UserViolationsView", violations_data: dict[str, int]):
        self.view_ref = view
        options = []
        first_category = None
        for name, count in violations_data.items():
            label = f"{name} ({count})"
            if first_category is None:
                first_category = name
            options.append(
                discord.SelectOption(
                    label=label,
                    value=name,
                    default=name == view.current_category,
                )
            )
        if view.current_category is None:
            view.current_category = first_category
        super().__init__(
            placeholder="Choose a category",
            min_values=1,
            max_values=1,
            options=options,
        )

    async def callback(self, interaction: discord.Interaction):
        if not has_level_admin_role(interaction.user):
            await interaction.response.send_message(
                "You don't have permission for this.", ephemeral=True
            )
            return

        selected = self.values[0]
        self.view_ref.current_category = selected
        for option in self.options:
            option.default = option.value == selected
        embed = self.view_ref.build_embed()
        await interaction.response.edit_message(embed=embed, view=self.view_ref)


class UserViolationsView(View):
    def __init__(self, invoker: discord.Member, target_user: discord.Member):
        super().__init__(timeout=300)
        self.invoker_id = invoker.id
        self.target_user = target_user
        self.target_user_id = str(target_user.id)
        self.current_category: str | None = None

        data = levels.get(self.target_user_id, {})
        violations_data = data.get("violations", {})
        if isinstance(violations_data, dict) and violations_data:
            self.add_item(UserViolationsCategorySelect(self, violations_data))

    def build_embed(self) -> discord.Embed:
        data = levels.get(self.target_user_id, {})
        violations_data = data.get("violations", {})

        if not isinstance(violations_data, dict) or not violations_data:
            description = (
                f"{self.target_user.mention} currently has no recorded warnings."
            )
        else:
            lines = []
            for category_name, count in violations_data.items():
                category_cfg = MODERATION_CATEGORIES.get(category_name, {})
                max_violations = int(category_cfg.get("max_violations", 1))
                punish_cfg = category_cfg.get("violation_punishments")
                punishment_summary = "No automatic punishment"
                if isinstance(punish_cfg, dict) and punish_cfg:
                    parts = []
                    for n in range(2, 6):
                        key = str(n)
                        value = punish_cfg.get(key)
                        if value is None:
                            continue
                        if isinstance(value, str):
                            ptype = value.strip().lower()
                            pdata = {"type": ptype}
                        elif isinstance(value, dict):
                            pdata = value
                            ptype = str(pdata.get("type", "")).strip().lower()
                        else:
                            continue
                        if not ptype or ptype in ("none", "off"):
                            continue
                        label = ptype.capitalize()
                        duration_seconds = pdata.get("duration_seconds")
                        if isinstance(duration_seconds, (int, float)) and duration_seconds > 0:
                            seconds_value = int(duration_seconds)
                            if seconds_value % 86400 == 0:
                                days = seconds_value // 86400
                                unit = "day" if days == 1 else "days"
                                dur_text = f"{days} {unit}"
                            elif seconds_value % 3600 == 0:
                                hours = seconds_value // 3600
                                unit = "hour" if hours == 1 else "hours"
                                dur_text = f"{hours} {unit}"
                            elif seconds_value % 60 == 0:
                                minutes_value = seconds_value // 60
                                unit = "minute" if minutes_value == 1 else "minutes"
                                dur_text = f"{minutes_value} {unit}"
                            else:
                                dur_text = f"{seconds_value} seconds"
                            entry_text = f"{n}: {label} ({dur_text})"
                        else:
                            entry_text = f"{n}: {label}"
                        parts.append(entry_text)
                    if parts:
                        punishment_summary = "; ".join(parts)
                else:
                    timeout_days = float(category_cfg.get("timeout_days", 0))
                    if timeout_days > 0 and max_violations > 0:
                        punishment_summary = f"{timeout_days} days timeout at {max_violations}"
                lines.append(
                    f"• {category_name}: {count}/{max_violations} ({punishment_summary})"
                )
            description = "\n".join(lines)

        embed = discord.Embed(
            title=f"Warnings for {self.target_user.display_name}",
            color=discord.Color.orange(),
            description=description,
        )
        embed.add_field(
            name="Level", value=data.get("level", 0), inline=True
        )
        embed.add_field(
            name="Unique messages",
            value=data.get("unique_count", 0),
            inline=True,
        )
        return embed

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if not has_level_admin_role(interaction.user):
            await interaction.response.send_message(
                "You don't have permission for this.", ephemeral=True
            )
            return False
        if interaction.user.id != self.invoker_id:
            await interaction.response.send_message(
                "Only the original requester can use this interface.",
                ephemeral=True,
            )
            return False
        return True

    @discord.ui.button(
        label="-1 warning",
        style=discord.ButtonStyle.secondary,
        row=1,
    )
    async def minus_one_button(
        self, interaction: discord.Interaction, button: Button
    ):
        if not self.current_category:
            await interaction.response.send_message(
                "No category selected.", ephemeral=True
            )
            return

        data = levels.get(self.target_user_id)
        if not isinstance(data, dict):
            await interaction.response.send_message(
                "No valid data found for this user.",
                ephemeral=True,
            )
            return

        violations_data = data.get("violations", {})
        if (
            not isinstance(violations_data, dict)
            or self.current_category not in violations_data
        ):
            await interaction.response.send_message(
                "This category no longer exists or has no warnings.",
                ephemeral=True,
            )
            return

        try:
            current_count = int(violations_data.get(self.current_category, 0))
        except (TypeError, ValueError):
            current_count = 0

        new_count = max(current_count - 1, 0)
        if new_count <= 0:
            del violations_data[self.current_category]
        else:
            violations_data[self.current_category] = new_count

        levels[self.target_user_id]["violations"] = violations_data
        save_levels()

        new_view = UserViolationsView(interaction.user, self.target_user)
        new_embed = new_view.build_embed()
        await interaction.response.edit_message(embed=new_embed, view=new_view)

    @discord.ui.button(
        label="+1 warning",
        style=discord.ButtonStyle.primary,
        row=1,
    )
    async def plus_one_button(
        self, interaction: discord.Interaction, button: Button
    ):
        if not self.current_category:
            await interaction.response.send_message(
                "No category selected.", ephemeral=True
            )
            return

        data = levels.get(self.target_user_id)
        if not isinstance(data, dict):
            await interaction.response.send_message(
                "No valid data found for this user.",
                ephemeral=True,
            )
            return

        violations_data = data.get("violations", {})
        if not isinstance(violations_data, dict):
            violations_data = {}

        try:
            current_count = int(violations_data.get(self.current_category, 0))
        except (TypeError, ValueError):
            current_count = 0

        new_count = current_count + 1
        violations_data[self.current_category] = new_count

        levels[self.target_user_id]["violations"] = violations_data
        save_levels()

        new_view = UserViolationsView(interaction.user, self.target_user)
        new_embed = new_view.build_embed()
        await interaction.response.edit_message(embed=new_embed, view=new_view)

    @discord.ui.button(
        label="Clear selected category",
        style=discord.ButtonStyle.danger,
        row=1,
    )
    async def clear_selected_button(
        self, interaction: discord.Interaction, button: Button
    ):
        if not self.current_category:
            await interaction.response.send_message(
                "No category selected.", ephemeral=True
            )
            return

        data = levels.get(self.target_user_id)
        if not isinstance(data, dict):
            await interaction.response.send_message(
                "No valid data found for this user.",
                ephemeral=True,
            )
            return

        violations_data = data.get("violations", {})
        if (
            not isinstance(violations_data, dict)
            or self.current_category not in violations_data
        ):
            await interaction.response.send_message(
                "This category no longer exists or has no warnings.",
                ephemeral=True,
            )
            return

        del violations_data[self.current_category]
        levels[self.target_user_id]["violations"] = violations_data
        save_levels()

        new_view = UserViolationsView(interaction.user, self.target_user)
        new_embed = new_view.build_embed()
        await interaction.response.edit_message(embed=new_embed, view=new_view)

    @discord.ui.button(
        label="Clear all warnings",
        style=discord.ButtonStyle.danger,
        row=1,
    )
    async def clear_all_button(
        self, interaction: discord.Interaction, button: Button
    ):
        data = levels.get(self.target_user_id)
        if isinstance(data, dict):
            data["violations"] = {}
            levels[self.target_user_id] = data
            save_levels()

        new_view = UserViolationsView(interaction.user, self.target_user)
        new_embed = new_view.build_embed()
        await interaction.response.edit_message(embed=new_embed, view=new_view)

    @discord.ui.button(
        label="Close",
        style=discord.ButtonStyle.secondary,
        row=2,
    )
    async def close_button(
        self, interaction: discord.Interaction, button: Button
    ):
        await interaction.response.defer(ephemeral=True, thinking=False)
        for child in self.children:
            child.disabled = True
        if interaction.message:
            await interaction.message.edit(view=self)


class MainControlPanelView(View):
    def __init__(self, invoker: discord.Member):
        super().__init__(timeout=300)
        self.invoker_id = invoker.id
        self.message: discord.Message | None = None

        label_to_key = {
            "Whitelist Manager": "whitelist_manager",
            "Moderation Settings": "moderation_settings",
            "My Level": "my_level",
            "Leaderboard": "leaderboard",
            "Warnings Manager": "warnings_manager",
            "Active Dev Badge": "active_dev_badge",
            "More settings": "more_settings",
            "Close Panel": "close_panel",
        }

        for child in list(self.children):
            if isinstance(child, Button):
                key = label_to_key.get(child.label)
                if key and not is_panel_button_enabled(key):
                    self.remove_item(child)

    def build_embed(self) -> discord.Embed:
        embed = discord.Embed(
            title="The Time Lord Control Panel",
            description=(
                "Use the buttons below to access the main features:\n"
                "• Whitelist management\n"
                "• Moderation settings and warnings\n"
                "• Level stats and leaderboard\n"
                "• User warning management"
            ),
            color=discord.Color.blurple(),
        )
        return embed

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.invoker_id:
            await interaction.response.send_message(
                "Only the original requester can use this interface.",
                ephemeral=True,
            )
            return False
        return True

    @discord.ui.button(
        label="Whitelist Manager",
        style=discord.ButtonStyle.primary,
        row=0,
    )
    async def whitelist_button(
        self, interaction: discord.Interaction, button: Button
    ):
        has_permission = False
        if interaction.user.guild_permissions.administrator:
            has_permission = True
        else:
            for role in interaction.user.roles:
                if role.name == WHITELIST_PERMISSION_ROLE:
                    has_permission = True
                    break

        if not has_permission:
            embed = discord.Embed(
                title="Access Denied",
                description=(
                    f"You need the '{WHITELIST_PERMISSION_ROLE}' role "
                    "to manage the whitelist."
                ),
                color=discord.Color.red(),
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return

        await send_whitelist_selection(interaction)

    @discord.ui.button(
        label="Moderation Settings",
        style=discord.ButtonStyle.secondary,
        row=0,
    )
    async def moderation_button(
        self, interaction: discord.Interaction, button: Button
    ):
        if not has_level_admin_role(interaction.user):
            await interaction.response.send_message(
                f"❌ You need the '{LEVEL_ADMIN_ROLE}' role to use this command.",
                ephemeral=True,
            )
            return

        view = ModerationConfigView(interaction.user)
        embed = view.build_embed(view.current_category)
        await interaction.response.send_message(
            embed=embed, view=view, ephemeral=True
        )
        try:
            message = await interaction.original_response()
            view.message = message
        except Exception:
            view.message = None

    @discord.ui.button(
        label="My Level",
        style=discord.ButtonStyle.success,
        row=1,
    )
    async def my_level_button(
        self, interaction: discord.Interaction, button: Button
    ):
        user_id = str(interaction.user.id)
        if user_id in levels:
            ensure_user_schema(user_id)
            lvl = levels[user_id]["level"]
            uniques = levels[user_id].get("unique_count", 0)
            next_level = lvl + 1

            required = required_uniques_for_level(next_level)
            progress = min(uniques, required)

            join_timestamp = levels[user_id].get("join_date", time.time())
            join_date = datetime.fromtimestamp(join_timestamp)
            days_in_server = (datetime.now() - join_date).days

            requirements = ""
            if next_level == 4 and days_in_server < LEVEL4_MIN_DAYS:
                remaining_days = LEVEL4_MIN_DAYS - days_in_server
                requirements = (
                    f"\n🔒 Level 4 requires {LEVEL4_MIN_DAYS} days in server "
                    f"({remaining_days} days remaining)"
                )
            elif next_level == 5 and days_in_server < LEVEL5_MIN_DAYS:
                remaining_days = LEVEL5_MIN_DAYS - days_in_server
                requirements = (
                    f"\n🔒 Level 5 requires {LEVEL5_MIN_DAYS} days in server "
                    f"({remaining_days} days remaining)"
                )

            embed = discord.Embed(
                title=f"{interaction.user.display_name}'s Level Stats",
                color=discord.Color.blue(),
            )

            if lvl in LEVEL_ROLES:
                role_id = LEVEL_ROLES[lvl]
                role = interaction.guild.get_role(role_id)
                role_mention = role.mention if role else f"Level {lvl} Role"
                embed.add_field(
                    name="Current Role", value=role_mention, inline=True
                )

            embed.add_field(name="Current Level", value=lvl, inline=True)
            embed.add_field(name="Unique Messages", value=uniques, inline=True)
            embed.add_field(
                name="Server Member Since",
                value=join_date.strftime("%B %d, %Y"),
                inline=False,
            )
        
            if MAX_LEVEL_ROLE > 0 and lvl < MAX_LEVEL_ROLE:
                embed.add_field(
                    name=f"Progress to Level {next_level}",
                    value=f"{progress}/{required} unique messages{requirements}",
                    inline=False,
                )

            embed.set_thumbnail(url=interaction.user.display_avatar.url)

            await interaction.response.send_message(embed=embed, ephemeral=True)
        else:
            await interaction.response.send_message(
                "You don't have any level data yet!", ephemeral=True
            )

    @discord.ui.button(
        label="Leaderboard",
        style=discord.ButtonStyle.secondary,
        row=1,
    )
    async def leaderboard_button(
        self, interaction: discord.Interaction, button: Button
    ):
        if LEADERBOARD_ADMIN_ONLY and not has_level_admin_role(interaction.user):
            await interaction.response.send_message(
                f"❌ You need the '{LEVEL_ADMIN_ROLE}' role to use this command.",
                ephemeral=True,
            )
            return

        sorted_users = sorted(
            [(user_id, data) for user_id, data in levels.items()],
            key=lambda x: (
                x[1].get("level", 0),
                x[1].get("unique_count", 0),
            ),
            reverse=True,
        )[:10]

        if not sorted_users:
            await interaction.response.send_message(
                "No level data available yet!", ephemeral=True
            )
            return

        embed = discord.Embed(
            title="🏆 Level Leaderboard",
            color=discord.Color.gold(),
        )

        leaderboard_text = ""
        for rank, (user_id, data) in enumerate(sorted_users, 1):
            member = interaction.guild.get_member(int(user_id))
            if not member:
                continue

            username = member.display_name
            level_value = data.get("level", 0)
            level_info = f"Level {level_value}"

            if data["level"] in LEVEL_ROLES:
                role_id = LEVEL_ROLES[data["level"]]
                role = interaction.guild.get_role(role_id)
                if role:
                    level_info = role.mention

            uniques = data.get("unique_count", 0)
            leaderboard_text += (
                f"**{rank}. {username}**\n"
                f"• {level_info}\n"
                f"• Messages: {uniques}\n\n"
            )

        embed.description = leaderboard_text
        embed.set_footer(text="Ranked by level then unique messages")

        await interaction.response.send_message(embed=embed, ephemeral=True)

    @discord.ui.button(
        label="Warnings Manager",
        style=discord.ButtonStyle.secondary,
        row=2,
    )
    async def warnings_button(
        self, interaction: discord.Interaction, button: Button
    ):
        if not has_level_admin_role(interaction.user):
            await interaction.response.send_message(
                f"❌ You need the '{LEVEL_ADMIN_ROLE}' role to manage warnings.",
                ephemeral=True,
            )
            return

        view = WarningsUserSelectView(interaction.user, interaction.guild)
        embed = discord.Embed(
            title="Manage user warnings",
            description=(
                "Select a user from the menu below, "
                "or use the search button."
            ),
            color=discord.Color.orange(),
        )
        await interaction.response.send_message(
            embed=embed, view=view, ephemeral=True
        )

    @discord.ui.button(
        label="Active Dev Badge",
        style=discord.ButtonStyle.secondary,
        row=2,
    )
    async def active_dev_button(
        self, interaction: discord.Interaction, button: Button
    ):
        embed = discord.Embed(
            title="🤖 Command Executed Successfully",
            description=(
                "You've successfully opened the Active Developer Badge panel!\n\n"
                "Use the button below to check your status. "
                "Note that it may take up to **24 hours** for Discord "
                "to process your eligibility."
            ),
            color=discord.Color.blue(),
        )
        embed.set_thumbnail(url=interaction.user.display_avatar.url)
        view = discord.ui.View()
        button_url = discord.ui.Button(
            label="Check Status",
            url="https://discord.com/developers/active-developer",
            style=discord.ButtonStyle.primary,
        )
        view.add_item(button_url)
        await interaction.response.send_message(
            embed=embed, view=view, ephemeral=True
        )

    @discord.ui.button(
        label="More settings",
        style=discord.ButtonStyle.primary,
        row=3,
    )
    async def more_settings_button(
        self, interaction: discord.Interaction, button: Button
    ):
        if not has_level_admin_role(interaction.user):
            await interaction.response.send_message(
                f"❌ You need the '{LEVEL_ADMIN_ROLE}' role to use this command.",
                ephemeral=True,
            )
            return

        await open_setup_view(interaction)

    @discord.ui.button(
        label="Close Panel",
        style=discord.ButtonStyle.danger,
        row=3,
    )
    async def close_button(
        self, interaction: discord.Interaction, button: Button
    ):
        await interaction.response.defer(ephemeral=True, thinking=False)
        for child in self.children:
            child.disabled = True
        if self.message:
            await self.message.edit(view=self)
async def send_whitelist_selection(interaction: discord.Interaction):
    servers_cfg = CONFIG.get("servers", {})
    if not isinstance(servers_cfg, dict) or not servers_cfg:
        embed = discord.Embed(
            title="Minecraft Whitelist Management",
            description="No servers are configured. Add servers in the config first.",
            color=discord.Color.red(),
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)
        return

    options: list[discord.SelectOption] = []
    for index, (name, cfg) in enumerate(sorted(servers_cfg.items())):
        if index >= 25:
            break
        if not isinstance(cfg, dict):
            continue
        host = str(cfg.get("host", ""))
        port = cfg.get("port")
        if host and port:
            desc = f"{host}:{port}"
        elif host:
            desc = host
        else:
            desc = ""
        options.append(
            discord.SelectOption(
                label=name,
                value=name,
                description=desc or None,
            )
        )

    if not options:
        embed = discord.Embed(
            title="Minecraft Whitelist Management",
            description="No valid servers are configured. Check config.yml.",
            color=discord.Color.red(),
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)
        return

    embed = discord.Embed(
        title="Minecraft Whitelist Management",
        description="Select which server whitelist you want to manage:",
        color=discord.Color.blue(),
    )

    view = discord.ui.View(timeout=180)
    original_user_id = interaction.user.id

    select = discord.ui.Select(
        placeholder="Choose a server",
        min_values=1,
        max_values=1,
        options=options,
    )

    async def select_callback(select_interaction: discord.Interaction):
        if select_interaction.user.id != original_user_id:
            await select_interaction.response.send_message(
                "Only the original requester can use this menu.", ephemeral=True
            )
            return
        if not select.values:
            await select_interaction.response.send_message(
                "No server selected.", ephemeral=True
            )
            return
        selected = select.values[0]
        servers_cfg_inner = CONFIG.get("servers", {})
        if not isinstance(servers_cfg_inner, dict):
            await select_interaction.response.send_message(
                "Configuration is not valid. Please fix config.yml and try again.",
                ephemeral=True,
            )
            return
        cfg = servers_cfg_inner.get(selected)
        if not isinstance(cfg, dict):
            await select_interaction.response.send_message(
                "This server no longer exists in the configuration.",
                ephemeral=True,
            )
            return
        host = cfg.get("host")
        port = cfg.get("port")
        password = cfg.get("password")
        if not host or not port or not password:
            await select_interaction.response.send_message(
                "This server is missing host, port or password in config.yml.",
                ephemeral=True,
            )
            return
        try:
            rcon = MCRcon(host, port, password)
        except Exception as e:
            await select_interaction.response.send_message(
                f"Could not create RCON connection: {e}", ephemeral=True
            )
            return

        server_embed = discord.Embed(
            title=f"Minecraft Whitelist Management ({selected})",
            description="Use the buttons below to manage the whitelist.",
            color=discord.Color.blue(),
        )
        whitelist_view = WhitelistView(rcon, server_type=selected)
        await select_interaction.response.send_message(
            embed=server_embed, view=whitelist_view, ephemeral=True
        )

    select.callback = select_callback
    view.add_item(select)

    await interaction.response.send_message(embed=embed, view=view, ephemeral=True)


if is_command_enabled("whitelist"):
    @bot.tree.command(name="whitelist", description="Manage Minecraft server whitelists")
    async def whitelist_choice_command(interaction: discord.Interaction):
        has_permission = False
        if interaction.user.guild_permissions.administrator:
            has_permission = True
        else:
            for role in interaction.user.roles:
                if role.name == WHITELIST_PERMISSION_ROLE:
                    has_permission = True
                    break
        
        if not has_permission:
            embed = discord.Embed(
                title="Access Denied",
                description=f"You need the '{WHITELIST_PERMISSION_ROLE}' role to manage the whitelist.",
                color=discord.Color.red()
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        
        await send_whitelist_selection(interaction)

if is_command_enabled("musictip"):
    @bot.tree.command(
        name="musictip",
        description="Get general tips for using your music bot",
    )
    async def music(interaction: discord.Interaction):
        embed = discord.Embed(
            title="🎵 Music Tips",
            description=(
                "Use your music bot's play command with:\n"
                "- Song titles or artist names\n"
                "- Playlist or track URLs supported by the bot\n"
                "- Any other search query your music bot supports"
            ),
            color=discord.Color.blue(),
        )

        await interaction.response.send_message(embed=embed, ephemeral=True)

@bot.tree.command(name="active-dev-badge", description="Claim your Active Developer Badge")
async def active_dev_badge(interaction: discord.Interaction):
    embed = discord.Embed(
        title="🤖 Command Executed Successfully",
        description="You've successfully executed the command to get the **Active Developer Badge**!\n\n"
                    "After Discord processes this command execution, you'll be able to claim your badge "
                    "by pressing the button below. Note that it may take up to **24 hours** for Discord to process your eligibility.\n\n"
                    f"_First executed on **{interaction.created_at.strftime('%B %d, %Y at %I:%M %p')}**_",
        color=discord.Color.blue()
    )
    embed.set_thumbnail(url=interaction.user.display_avatar.url)
    view = discord.ui.View()
    button = discord.ui.Button(label="Check Status", url="https://discord.com/developers/active-developer", style=discord.ButtonStyle.primary)
    view.add_item(button)
    await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

if is_command_enabled("time"):
    @bot.tree.command(name="time", description="What does The Time Lord say?")
    async def time_command(interaction: discord.Interaction):
        await interaction.response.send_message(TIME_RESPONSE_TEXT)

if is_command_enabled("amogus"):
    @bot.tree.command(name="amogus", description="Posts an Among Us image")
    async def amogus_command(interaction: discord.Interaction):
        embed = discord.Embed(title="Sus! 📮", color=discord.Color.red())
        embed.set_image(url=IMAGES.get("amogus", "https://vulcanoimage.pages.dev/amogus.png"))
        await interaction.response.send_message(embed=embed)

if is_command_enabled("klokdag"):
    @bot.tree.command(name="klokdag", description="Posts a klokdag image")
    async def klokdag_command(interaction: discord.Interaction):
        embed = discord.Embed(color=discord.Color.blue())
        embed.set_image(url=IMAGES.get("klokdag", "https://vulcanoimage.pages.dev/klokdag.png"))
        await interaction.response.send_message(embed=embed)

if is_command_enabled("kloknacht"):
    @bot.tree.command(name="kloknacht", description="Posts a kloknacht image")
    async def kloknacht_command(interaction: discord.Interaction):
        embed = discord.Embed(color=discord.Color.blue())
        embed.set_image(url=IMAGES.get("kloknacht", "https://vulcanoimage.pages.dev/kloknacht.png"))
        await interaction.response.send_message(embed=embed)

if is_command_enabled("lobby"):
    @bot.tree.command(name="lobby", description="Posts a lobby image")
    async def lobby_command(interaction: discord.Interaction):
        embed = discord.Embed(color=discord.Color.blue())
        embed.set_image(url=IMAGES.get("lobby", "https://vulcanoimage.pages.dev/lobby.png"))
        await interaction.response.send_message(embed=embed)

if is_command_enabled("vulcanotechcraft"):
    @bot.tree.command(name="vulcanotechcraft", description="Posts a vulcanotechcraft image")
    async def vulcanotechcraft_command(interaction: discord.Interaction):
        embed = discord.Embed(color=discord.Color.blue())
        embed.set_image(url=IMAGES.get("vulcanotechcraft", "https://vulcanoimage.pages.dev/vulcanotechcraft.png"))
        await interaction.response.send_message(embed=embed)

if is_command_enabled("moderation"):
    @bot.tree.command(name="moderation", description="[ADMIN] Manage moderation settings")
    async def moderation_command(interaction: discord.Interaction):
        if not has_level_admin_role(interaction.user):
            await interaction.response.send_message(
                f"❌ You need the '{LEVEL_ADMIN_ROLE}' role to use this command.",
                ephemeral=True,
            )
            return

        view = ModerationConfigView(interaction.user)
        embed = view.build_embed(view.current_category)
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
        try:
            message = await interaction.original_response()
            view.message = message
        except Exception:
            view.message = None

@bot.tree.command(name="level", description="Check your current level and stats")
async def level_command(interaction: discord.Interaction):
    user_id = str(interaction.user.id)
    if user_id in levels:
        ensure_user_schema(user_id)
        lvl = levels[user_id]["level"]
        uniques = levels[user_id].get("unique_count", 0)
        next_level = lvl + 1
        
        # Calculate progress
        required = required_uniques_for_level(next_level)
        progress = min(uniques, required)
        
        # Calculate membership duration
        join_timestamp = levels[user_id].get("join_date", time.time())
        join_date = datetime.fromtimestamp(join_timestamp)
        days_in_server = (datetime.now() - join_date).days
        
        requirements = ""
        if next_level == 4 and days_in_server < LEVEL4_MIN_DAYS:
            remaining_days = LEVEL4_MIN_DAYS - days_in_server
            requirements = f"\n🔒 Level 4 requires {LEVEL4_MIN_DAYS} days in server ({remaining_days} days remaining)"
        elif next_level == 5 and days_in_server < LEVEL5_MIN_DAYS:
            remaining_days = LEVEL5_MIN_DAYS - days_in_server
            requirements = f"\n🔒 Level 5 requires {LEVEL5_MIN_DAYS} days in server ({remaining_days} days remaining)"
        
        # Create embed
        embed = discord.Embed(
            title=f"{interaction.user.display_name}'s Level Stats",
            color=discord.Color.blue()
        )
        
        # Add current role information
        if lvl in LEVEL_ROLES:
            role_id = LEVEL_ROLES[lvl]
            role = interaction.guild.get_role(role_id)
            role_mention = role.mention if role else f"Level {lvl} Role"
            embed.add_field(name="Current Role", value=role_mention, inline=True)
        
        embed.add_field(name="Current Level", value=lvl, inline=True)
        embed.add_field(name="Unique Messages", value=uniques, inline=True)
        embed.add_field(name="Server Member Since", value=join_date.strftime("%B %d, %Y"), inline=False)
        
        if MAX_LEVEL_ROLE > 0 and lvl < MAX_LEVEL_ROLE:
            embed.add_field(
                name=f"Progress to Level {next_level}",
                value=f"{progress}/{required} unique messages{requirements}",
                inline=False
            )
        
        embed.set_thumbnail(url=interaction.user.display_avatar.url)
        
        await interaction.response.send_message(embed=embed)
    else:
        await interaction.response.send_message("You don't have any level data yet!", ephemeral=True)

@bot.tree.command(name="leaderboard", description="Show the top 10 members by level")
async def leaderboard_command(interaction: discord.Interaction):
    if LEADERBOARD_ADMIN_ONLY and not has_level_admin_role(interaction.user):
        await interaction.response.send_message(
            f"❌ You need the '{LEVEL_ADMIN_ROLE}' role to use this command.",
            ephemeral=True,
        )
        return

    sorted_users = sorted(
        [(user_id, data) for user_id, data in levels.items()],
        key=lambda x: (x[1].get("level", 0), x[1].get("unique_count", 0)),
        reverse=True,
    )[:10]

    if not sorted_users:
        await interaction.response.send_message("No level data available yet!")
        return

    embed = discord.Embed(
        title="🏆 Level Leaderboard",
        color=discord.Color.gold(),
    )

    leaderboard_text = ""
    for rank, (user_id, data) in enumerate(sorted_users, 1):
        member = interaction.guild.get_member(int(user_id))
        if not member:
            continue

        username = member.display_name
        level_value = data.get("level", 0)
        level_info = f"Level {level_value}"

        if data["level"] in LEVEL_ROLES:
            role_id = LEVEL_ROLES[data["level"]]
            role = interaction.guild.get_role(role_id)
            if role:
                level_info = role.mention

        uniques = data.get("unique_count", 0)
        leaderboard_text += (
            f"**{rank}. {username}**\n"
            f"• {level_info}\n"
            f"• Messages: {uniques}\n\n"
        )

    embed.description = leaderboard_text
    embed.set_footer(text="Ranked by level then unique messages")

    await interaction.response.send_message(embed=embed)


@bot.tree.command(name="panel", description="Open The Time Lord control panel")
async def panel_command(interaction: discord.Interaction):
    view = MainControlPanelView(interaction.user)
    embed = view.build_embed()
    await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
    try:
        message = await interaction.original_response()
        view.message = message
    except Exception:
        view.message = None

if is_command_enabled("timeout"):
    @bot.tree.command(name="timeout", description="Give a user a timeout")
    @app_commands.describe(
        member="User to timeout",
        time_value="Duration amount",
        time_unit="Time unit for the duration",
        reason="Reason for the timeout",
    )
    @app_commands.choices(
        time_unit=[
            app_commands.Choice(name="Seconds", value="seconds"),
            app_commands.Choice(name="Minutes", value="minutes"),
            app_commands.Choice(name="Hours", value="hours"),
            app_commands.Choice(name="Days", value="days"),
            app_commands.Choice(name="Weeks", value="weeks"),
            app_commands.Choice(name="Months", value="months"),
            app_commands.Choice(name="Years", value="years"),
        ]
    )
    @app_commands.default_permissions(moderate_members=True)
    @app_commands.guild_only()
    async def timeout(
        interaction: discord.Interaction,
        member: discord.Member,
        time_value: app_commands.Range[int, 1, 525600],
        time_unit: app_commands.Choice[str],
        reason: str = "No reason provided",
    ):
        total_seconds, duration_text = get_duration_info(time_value, time_unit.value)
        until = utcnow() + timedelta(seconds=total_seconds)
        guild = interaction.guild
        if guild is None:
            await interaction.response.send_message("This command can only be used in a server.", ephemeral=True)
            return
        try:
            await member.timeout(until, reason=reason)
            description = (
                f"You have received a timeout in {guild.name}.\n"
                f"Duration: {duration_text}\n"
                f"Reason: {reason}\n"
                f"Staff: {interaction.user}"
            )
            await send_punishment_dm(member, guild, "Timeout", description)
            log_punishment(
                guild.id,
                member.id,
                "timeout_set",
                {
                    "duration_minutes": total_seconds // 60,
                    "duration_text": duration_text,
                    "reason": reason,
                    "staff_id": interaction.user.id,
                },
            )
            asyncio.create_task(schedule_timeout_end(guild.id, member.id, total_seconds))
            await interaction.response.send_message(
                f"{member.mention} has received a timeout for {duration_text}. Reason: {reason}",
                ephemeral=True,
            )
        except discord.Forbidden:
            await interaction.response.send_message("I do not have permission to timeout this user.", ephemeral=True)
        except Exception as e:
            await interaction.response.send_message(f"Something went wrong: {e}", ephemeral=True)


if is_command_enabled("untimeout"):
    @bot.tree.command(name="untimeout", description="Remove timeout from a user")
    @app_commands.describe(member="User whose timeout you want to remove", reason="Reason")
    @app_commands.default_permissions(moderate_members=True)
    @app_commands.guild_only()
    async def untimeout(
        interaction: discord.Interaction,
        member: discord.Member,
        reason: str = "No reason provided",
    ):
        guild = interaction.guild
        if guild is None:
            await interaction.response.send_message("This command can only be used in a server.", ephemeral=True)
            return
        try:
            await member.timeout(None, reason=reason)
            description = (
                f"Your timeout in {guild.name} has been removed.\n"
                f"Reason: {reason}\n"
                f"Staff: {interaction.user}"
            )
            await send_info_dm(member, guild, "Timeout removed", description)
            log_punishment(
                guild.id,
                member.id,
                "timeout_removed",
                {
                    "reason": reason,
                    "staff_id": interaction.user.id,
                },
            )
            await interaction.response.send_message(
                f"Timeout for {member.mention} has been removed. Reason: {reason}",
                ephemeral=True,
            )
        except discord.Forbidden:
            await interaction.response.send_message("I do not have permission to remove the timeout.", ephemeral=True)
        except Exception as e:
            await interaction.response.send_message(f"Something went wrong: {e}", ephemeral=True)


if is_command_enabled("mute"):
    @bot.tree.command(name="mute", description="Mute a user with a Muted role")
    @app_commands.describe(
        member="User to mute",
        reason="Reason for mute",
        duration_value="Duration amount for a mute (leave empty for permanent)",
        duration_unit="Time unit for the mute duration",
    )
    @app_commands.choices(
        duration_unit=[
            app_commands.Choice(name="Seconds", value="seconds"),
            app_commands.Choice(name="Minutes", value="minutes"),
            app_commands.Choice(name="Hours", value="hours"),
            app_commands.Choice(name="Days", value="days"),
            app_commands.Choice(name="Weeks", value="weeks"),
            app_commands.Choice(name="Months", value="months"),
            app_commands.Choice(name="Years", value="years"),
        ]
    )
    @app_commands.default_permissions(moderate_members=True)
    @app_commands.guild_only()
    async def mute(
        interaction: discord.Interaction,
        member: discord.Member,
        reason: str = "No reason provided",
        duration_value: app_commands.Range[int, 1, 525600] | None = None,
        duration_unit: app_commands.Choice[str] | None = None,
    ):
        guild = interaction.guild
        if guild is None:
            await interaction.response.send_message("This command can only be used in a server.", ephemeral=True)
            return

        if (duration_value is None) != (duration_unit is None):
            await interaction.response.send_message(
                "Please provide both duration value and duration unit, or leave both empty for a permanent mute.",
                ephemeral=True,
            )
            return

        await interaction.response.defer(ephemeral=True)
        try:
            muted_role = await ensure_muted_role(guild)
            if muted_role is None:
                await interaction.followup.send(
                    "No mute role is configured. Use /setup to choose a mute role or enable automatic creation.",
                    ephemeral=True,
                )
                return
            if muted_role in member.roles:
                await interaction.followup.send(f"{member.mention} is already muted.", ephemeral=True)
                return
            await member.add_roles(muted_role, reason=reason)
            if duration_value is not None and duration_unit is not None:
                total_seconds, duration_text = get_duration_info(duration_value, duration_unit.value)
                description = (
                    f"You have been temporarily muted in {guild.name}.\n"
                    f"Duration: {duration_text}\n"
                    f"Reason: {reason}\n"
                    f"Staff: {interaction.user}"
                )
                asyncio.create_task(schedule_unmute(guild.id, member.id, total_seconds))
            else:
                duration_text = None
                description = (
                    f"You have been muted in {guild.name}.\n"
                    f"Reason: {reason}\n"
                    f"Staff: {interaction.user}"
                )
            await send_punishment_dm(member, guild, "Mute", description)
            log_punishment(
                guild.id,
                member.id,
                "mute_set",
                {
                    "duration_minutes": (total_seconds // 60) if duration_value is not None and duration_unit is not None else None,
                    "duration_text": duration_text,
                    "reason": reason,
                    "staff_id": interaction.user.id,
                },
            )
            await interaction.followup.send(
                f"{member.mention} has been muted. Reason: {reason}",
                ephemeral=True,
            )
        except discord.Forbidden:
            await interaction.followup.send("I do not have permission to add roles.", ephemeral=True)
        except Exception as e:
            await interaction.followup.send(f"Something went wrong: {e}", ephemeral=True)


if is_command_enabled("unmute"):
    @bot.tree.command(name="unmute", description="Unmute a user")
    @app_commands.describe(member="User to unmute", reason="Reason")
    @app_commands.default_permissions(moderate_members=True)
    @app_commands.guild_only()
    async def unmute(
        interaction: discord.Interaction,
        member: discord.Member,
        reason: str = "No reason provided",
    ):
        guild = interaction.guild
        if guild is None:
            await interaction.response.send_message("This command can only be used in a server.", ephemeral=True)
            return

        guild_conf = get_modbot_guild_config(guild.id)
        mute_role_id = guild_conf.get("mute_role_id")
        muted_role = None

        if mute_role_id:
            muted_role = guild.get_role(mute_role_id)

        if muted_role is None:
            muted_role = discord.utils.get(guild.roles, name="Muted")

        if muted_role is None:
            await interaction.response.send_message("There is no Muted role yet.", ephemeral=True)
            return

        try:
            if muted_role not in member.roles:
                await interaction.response.send_message(f"{member.mention} is not muted.", ephemeral=True)
                return
            await member.remove_roles(muted_role, reason=reason)
            description = (
                f"Your mute in {guild.name} has been removed.\n"
                f"Reason: {reason}\n"
                f"Staff: {interaction.user}"
            )
            await send_info_dm(member, guild, "Unmute", description)
            log_punishment(
                guild.id,
                member.id,
                "mute_removed",
                {
                    "reason": reason,
                    "staff_id": interaction.user.id,
                    "automatic": False,
                },
            )
            await interaction.response.send_message(
                f"{member.mention} has been unmuted. Reason: {reason}",
                ephemeral=True,
            )
        except discord.Forbidden:
            await interaction.response.send_message("I do not have permission to remove roles.", ephemeral=True)
        except Exception as e:
            await interaction.response.send_message(f"Something went wrong: {e}", ephemeral=True)


class ConfigSectionModal(Modal):
    def __init__(self, section_name: str, json_text: str, explanation: str):
        super().__init__(title=f"Advanced config (JSON): {section_name}")
        self.section_name = section_name
        short_explanation = explanation
        if len(short_explanation) > 3900:
            short_explanation = short_explanation[:3900]
        helper_header = (
            "This is the raw JSON for this config section.\n"
            "Most users can close this window and instead use the normal setup panels.\n\n"
        )
        if short_explanation:
            short_explanation = helper_header + short_explanation
        else:
            short_explanation = helper_header
        self.info = TextInput(
            label="Explanation (read-only help)",
            style=discord.TextStyle.paragraph,
            default=short_explanation,
            required=False,
        )
        self.data = TextInput(
            label="Config value (JSON – advanced)",
            style=discord.TextStyle.paragraph,
            default=json_text,
            required=False,
        )
        self.add_item(self.info)
        self.add_item(self.data)

    async def on_submit(self, interaction: discord.Interaction):
        raw = self.data.value.strip()
        if not raw:
            await interaction.response.send_message(
                "No changes were saved because the JSON field was left empty.",
                ephemeral=True,
            )
            return
        try:
            new_value = json.loads(raw)
        except Exception as e:
            await interaction.response.send_message(
                "The text you entered is not valid JSON.\n"
                "Make sure you use double quotes (\") around keys and values and commas between items.\n"
                f"Technical details: {e}",
                ephemeral=True,
            )
            return
        if not isinstance(CONFIG, dict):
            await interaction.response.send_message(
                "Configuration is not a valid dictionary.", ephemeral=True
            )
            return
        CONFIG[self.section_name] = new_value
        reload_config_state()
        save_config()
        await interaction.response.send_message(
            "Configuration section saved. Changes take effect immediately.",
            ephemeral=True,
        )


class DiscordConfigModal(Modal):
    def __init__(self):
        super().__init__(title="Discord settings")
        discord_cfg = CONFIG.get("discord", {})
        prefix = discord_cfg.get("command_prefix", "!")
        activity_type = discord_cfg.get("activity_type", "watching")
        activity_text = discord_cfg.get("activity_text", "your watch")
        self.command_prefix = TextInput(
            label="Command prefix",
            default=str(prefix),
            required=False,
        )
        self.activity_type = TextInput(
            label="Activity type (playing, watching, listening)",
            default=str(activity_type),
            required=False,
        )
        self.activity_text = TextInput(
            label="Activity text",
            default=str(activity_text),
            required=False,
        )
        self.add_item(self.command_prefix)
        self.add_item(self.activity_type)
        self.add_item(self.activity_text)

    async def on_submit(self, interaction: discord.Interaction):
        if not isinstance(CONFIG, dict):
            await interaction.response.send_message(
                "Configuration is not a valid dictionary.", ephemeral=True
            )
            return
        discord_cfg = CONFIG.get("discord")
        if not isinstance(discord_cfg, dict):
            discord_cfg = {}
            CONFIG["discord"] = discord_cfg
        prefix_value = self.command_prefix.value.strip()
        if prefix_value:
            discord_cfg["command_prefix"] = prefix_value
        activity_type_value = self.activity_type.value.strip()
        if activity_type_value:
            discord_cfg["activity_type"] = activity_type_value
        activity_text_value = self.activity_text.value.strip()
        if activity_text_value:
            discord_cfg["activity_text"] = activity_text_value
        reload_config_state()
        save_config()
        await interaction.response.send_message(
            "Discord settings updated.", ephemeral=True
        )


class ServersConfigModal(Modal):
    def __init__(self):
        super().__init__(title="Main server settings")
        whitelist_enabled_value = CONFIG.get("whitelist_enabled", True)
        servers_cfg = CONFIG.get("servers", {})
        main_cfg = servers_cfg.get("main", {})
        main_host = main_cfg.get("host", "127.0.0.1")
        main_port = main_cfg.get("port", 25575)
        main_password = main_cfg.get("password", "")
        self.whitelist_enabled = TextInput(
            label="Whitelist enabled? (true/false)",
            default="true" if whitelist_enabled_value else "false",
            required=False,
        )
        self.main_host = TextInput(
            label="Main server host",
            default=str(main_host),
            required=False,
        )
        self.main_port = TextInput(
            label="Main server RCON port",
            default=str(main_port),
            required=False,
        )
        self.main_password = TextInput(
            label="Main server RCON password",
            default=str(main_password),
            required=False,
        )
        self.add_item(self.whitelist_enabled)
        self.add_item(self.main_host)
        self.add_item(self.main_port)
        self.add_item(self.main_password)

    async def on_submit(self, interaction: discord.Interaction):
        if not isinstance(CONFIG, dict):
            await interaction.response.send_message(
                "Configuration is not a valid dictionary.", ephemeral=True
            )
            return

        def parse_bool(value: str) -> bool | None:
            lowered = value.strip().lower()
            if lowered in ("true", "1", "yes", "y", "ja"):
                return True
            if lowered in ("false", "0", "no", "n", "nee"):
                return False
            return None

        we_raw = self.whitelist_enabled.value.strip()
        if we_raw:
            parsed_we = parse_bool(we_raw)
            if parsed_we is not None:
                CONFIG["whitelist_enabled"] = parsed_we

        servers_cfg = CONFIG.get("servers")
        if not isinstance(servers_cfg, dict):
            servers_cfg = {}
            CONFIG["servers"] = servers_cfg
        main_cfg = servers_cfg.get("main")
        if not isinstance(main_cfg, dict):
            main_cfg = {}
            servers_cfg["main"] = main_cfg

        host_raw = self.main_host.value.strip()
        if host_raw:
            main_cfg["host"] = host_raw

        port_raw = self.main_port.value.strip()
        if port_raw:
            try:
                port_value = int(port_raw)
                if port_value > 0:
                    main_cfg["port"] = port_value
            except ValueError:
                pass

        password_raw = self.main_password.value.strip()
        if password_raw:
            main_cfg["password"] = password_raw

        reload_config_state()
        save_config()
        await interaction.response.send_message(
            "Server settings updated.", ephemeral=True
        )


class LevelingConfigModal(Modal):
    def __init__(self):
        super().__init__(title="Leveling settings")
        leveling_cfg = CONFIG.get("leveling", {})
        u = leveling_cfg.get("unique_messages_per_level", 20)
        cd = leveling_cfg.get("cooldown_seconds", 60)
        l4 = leveling_cfg.get("level4_min_days", 14)
        l5 = leveling_cfg.get("level5_min_days", 60)
        rh = leveling_cfg.get("recent_message_hashes", 100)
        leaderboard_admin_only = bool(leveling_cfg.get("leaderboard_admin_only", False))
        self.unique_messages_per_level = TextInput(
            label="Unique messages per level",
            default=str(u),
            required=False,
        )
        self.cooldown_seconds = TextInput(
            label="Message cooldown seconds",
            default=str(cd),
            required=False,
        )
        self.level4_min_days = TextInput(
            label="Min days for level 4",
            default=str(l4),
            required=False,
        )
        self.level5_min_days = TextInput(
            label="Min days for level 5",
            default=str(l5),
            required=False,
        )
        self.leaderboard_admin_only = TextInput(
            label="Leaderboard admin-only? (true/false)",
            default="true" if leaderboard_admin_only else "false",
            required=False,
        )
        self.add_item(self.unique_messages_per_level)
        self.add_item(self.cooldown_seconds)
        self.add_item(self.level4_min_days)
        self.add_item(self.level5_min_days)
        self.add_item(self.leaderboard_admin_only)

    async def on_submit(self, interaction: discord.Interaction):
        if not isinstance(CONFIG, dict):
            await interaction.response.send_message(
                "Configuration is not a valid dictionary.", ephemeral=True
            )
            return
        leveling_cfg = CONFIG.get("leveling")
        if not isinstance(leveling_cfg, dict):
            leveling_cfg = {}
            CONFIG["leveling"] = leveling_cfg

        def update_int(field: TextInput, key: str):
            raw = field.value.strip()
            if not raw:
                return
            try:
                v = int(raw)
                if v < 0:
                    v = 0
                leveling_cfg[key] = v
            except ValueError:
                return

        def update_bool(field: TextInput, key: str):
            raw = field.value.strip()
            if not raw:
                return
            lowered = raw.lower()
            if lowered in ("true", "1", "yes", "y", "ja"):
                leveling_cfg[key] = True
            elif lowered in ("false", "0", "no", "n", "nee"):
                leveling_cfg[key] = False

        update_int(self.unique_messages_per_level, "unique_messages_per_level")
        update_int(self.cooldown_seconds, "cooldown_seconds")
        update_int(self.level4_min_days, "level4_min_days")
        update_int(self.level5_min_days, "level5_min_days")
        update_bool(self.leaderboard_admin_only, "leaderboard_admin_only")

        reload_config_state()
        save_config()
        await interaction.response.send_message(
            "Leveling settings updated.", ephemeral=True
        )


class LevelRolesLevelSelect(discord.ui.Select):
    def __init__(self, view: "LevelRolesConfigView"):
        self.view_ref = view
        levels = set(LEVEL_ROLES.keys())
        base_levels = {1, 2, 3, 4, 5}
        all_levels = sorted(base_levels | levels)
        options: list[discord.SelectOption] = []
        for lvl in all_levels:
            role = None
            role_id = LEVEL_ROLES.get(lvl)
            if role_id:
                role = view.guild.get_role(role_id)
            description = None
            if role is not None:
                description = f"Current role: {role.name}"
            options.append(
                discord.SelectOption(
                    label=f"Level {lvl}",
                    value=str(lvl),
                    description=description,
                )
            )
        super().__init__(
            placeholder="Choose a level",
            min_values=1,
            max_values=1,
            options=options,
            row=0,
        )

    async def callback(self, interaction: discord.Interaction):
        selected = self.values[0]
        try:
            level_value = int(selected)
        except ValueError:
            level_value = 1
        self.view_ref.current_level = level_value
        embed = self.view_ref.build_embed()
        await interaction.response.edit_message(embed=embed, view=self.view_ref)


class LevelRolesConfigView(View):
    def __init__(self, guild: discord.Guild):
        super().__init__(timeout=300)
        self.guild = guild
        self.message: discord.Message | None = None
        self.current_level: int = 1
        self.add_item(LevelRolesLevelSelect(self))

    def build_embed(self) -> discord.Embed:
        guild = self.guild
        levels = set(LEVEL_ROLES.keys())
        base_levels = {1, 2, 3, 4, 5}
        all_levels = sorted(base_levels | levels)
        lines: list[str] = []
        for lvl in all_levels:
            role = None
            role_id = LEVEL_ROLES.get(lvl)
            if role_id:
                role = guild.get_role(role_id)
            marker = "▶" if lvl == self.current_level else "•"
            if role is not None:
                lines.append(f"{marker} Level {lvl} → {role.mention}")
            else:
                lines.append(f"{marker} Level {lvl} → (not set)")
        if not lines:
            description = "No level roles configured yet."
        else:
            description = "\n".join(lines)
        auto_status = "enabled" if get_auto_create_level_roles() else "disabled"
        description += f"\n\nAuto-create level roles: {auto_status}"
        embed = discord.Embed(
            title="Level roles configuration",
            description=description,
            color=discord.Color.blurple(),
        )
        return embed

    @discord.ui.select(
        cls=discord.ui.RoleSelect,
        placeholder="Choose role for selected level",
        min_values=0,
        max_values=1,
        row=1,
    )
    async def level_role_select(
        self, interaction: discord.Interaction, select: discord.ui.RoleSelect
    ) -> None:
        if not has_level_admin_role(interaction.user):
            await interaction.response.send_message(
                "You do not have permission to use this.", ephemeral=True
            )
            return
        if not self.current_level:
            await interaction.response.send_message(
                "Select a level first.", ephemeral=True
            )
            return
        if select.values:
            role = select.values[0]
            set_level_role_mapping(self.current_level, role.id)
        else:
            set_level_role_mapping(self.current_level, None)
        embed = self.build_embed()
        await interaction.response.edit_message(embed=embed, view=self)

    @discord.ui.button(
        label="Toggle auto-create level roles",
        style=discord.ButtonStyle.primary,
        row=2,
    )
    async def toggle_auto_create_button(
        self, interaction: discord.Interaction, button: Button
    ) -> None:
        if not has_level_admin_role(interaction.user):
            await interaction.response.send_message(
                "You do not have permission to use this.", ephemeral=True
            )
            return
        current = get_auto_create_level_roles()
        set_auto_create_level_roles(not current)
        embed = self.build_embed()
        await interaction.response.edit_message(embed=embed, view=self)

    @discord.ui.button(
        label="Edit numeric leveling settings",
        style=discord.ButtonStyle.secondary,
        row=2,
    )
    async def edit_numeric_button(
        self, interaction: discord.Interaction, button: Button
    ) -> None:
        if not has_level_admin_role(interaction.user):
            await interaction.response.send_message(
                "You do not have permission to use this.", ephemeral=True
            )
            return
        modal = LevelingConfigModal()
        await interaction.response.send_modal(modal)

    @discord.ui.button(
        label="Back to setup",
        style=discord.ButtonStyle.secondary,
        row=3,
    )
    async def back_to_setup_button(
        self, interaction: discord.Interaction, button: Button
    ) -> None:
        await open_setup_view(interaction)


class RolesConfigModal(Modal):
    def __init__(self):
        super().__init__(title="Role settings")
        roles_cfg = CONFIG.get("roles", {})
        whitelist_role = roles_cfg.get("whitelist_permission", "whitelist_perms")
        admin_role = roles_cfg.get("level_admin", "level_admin")
        self.whitelist_permission = TextInput(
            label="Whitelist permission role name",
            default=str(whitelist_role),
            required=False,
        )
        self.level_admin = TextInput(
            label="Level admin role name",
            default=str(admin_role),
            required=False,
        )
        self.add_item(self.whitelist_permission)
        self.add_item(self.level_admin)

    async def on_submit(self, interaction: discord.Interaction):
        if not isinstance(CONFIG, dict):
            await interaction.response.send_message(
                "Configuration is not a valid dictionary.", ephemeral=True
            )
            return
        roles_cfg = CONFIG.get("roles")
        if not isinstance(roles_cfg, dict):
            roles_cfg = {}
            CONFIG["roles"] = roles_cfg
        w_raw = self.whitelist_permission.value.strip()
        if w_raw:
            roles_cfg["whitelist_permission"] = w_raw
        a_raw = self.level_admin.value.strip()
        if a_raw:
            roles_cfg["level_admin"] = a_raw
        reload_config_state()
        save_config()
        await interaction.response.send_message(
            "Role settings updated.", ephemeral=True
        )


class MessagesConfigModal(Modal):
    def __init__(self):
        super().__init__(title="Message settings")
        messages_cfg = CONFIG.get("messages", {})
        time_text = messages_cfg.get("time_response", "time is endless")
        self.time_response = TextInput(
            label="Text for /time command",
            default=str(time_text),
            required=False,
        )
        self.add_item(self.time_response)

    async def on_submit(self, interaction: discord.Interaction):
        if not isinstance(CONFIG, dict):
            await interaction.response.send_message(
                "Configuration is not a valid dictionary.", ephemeral=True
            )
            return
        messages_cfg = CONFIG.get("messages")
        if not isinstance(messages_cfg, dict):
            messages_cfg = {}
            CONFIG["messages"] = messages_cfg
        t_raw = self.time_response.value.strip()
        if t_raw:
            messages_cfg["time_response"] = t_raw
        reload_config_state()
        save_config()
        await interaction.response.send_message(
            "Message settings updated.", ephemeral=True
        )


class ImagesConfigModal(Modal):
    def __init__(self):
        super().__init__(title="Image URLs")
        images_cfg = CONFIG.get("images", {})
        amogus_url = images_cfg.get("amogus", "")
        klokdag_url = images_cfg.get("klokdag", "")
        kloknacht_url = images_cfg.get("kloknacht", "")
        lobby_url = images_cfg.get("lobby", "")
        vt_url = images_cfg.get("vulcanotechcraft", "")
        self.amogus = TextInput(
            label="amogus image URL",
            default=str(amogus_url),
            required=False,
        )
        self.klokdag = TextInput(
            label="klokdag image URL",
            default=str(klokdag_url),
            required=False,
        )
        self.kloknacht = TextInput(
            label="kloknacht image URL",
            default=str(kloknacht_url),
            required=False,
        )
        self.lobby = TextInput(
            label="lobby image URL",
            default=str(lobby_url),
            required=False,
        )
        self.vulcanotechcraft = TextInput(
            label="vulcanotechcraft image URL",
            default=str(vt_url),
            required=False,
        )
        self.add_item(self.amogus)
        self.add_item(self.klokdag)
        self.add_item(self.kloknacht)
        self.add_item(self.lobby)
        self.add_item(self.vulcanotechcraft)

    async def on_submit(self, interaction: discord.Interaction):
        if not isinstance(CONFIG, dict):
            await interaction.response.send_message(
                "Configuration is not a valid dictionary.", ephemeral=True
            )
            return
        images_cfg = CONFIG.get("images")
        if not isinstance(images_cfg, dict):
            images_cfg = {}
            CONFIG["images"] = images_cfg

        def update_url(field: TextInput, key: str):
            raw = field.value.strip()
            if raw:
                images_cfg[key] = raw

        update_url(self.amogus, "amogus")
        update_url(self.klokdag, "klokdag")
        update_url(self.kloknacht, "kloknacht")
        update_url(self.lobby, "lobby")
        update_url(self.vulcanotechcraft, "vulcanotechcraft")

        reload_config_state()
        save_config()
        await interaction.response.send_message(
            "Image URLs updated.", ephemeral=True
        )


class CommandsConfigModal(Modal):
    def __init__(self):
        super().__init__(title="Commands settings")
        self.command_name = TextInput(
            label="Command name",
            required=True,
        )
        self.enabled = TextInput(
            label="Enabled? (true/false)",
            default="true",
            required=False,
        )
        self.add_item(self.command_name)
        self.add_item(self.enabled)

    async def on_submit(self, interaction: discord.Interaction):
        if not isinstance(CONFIG, dict):
            await interaction.response.send_message(
                "Configuration is not a valid dictionary.", ephemeral=True
            )
            return

        def parse_bool(value: str) -> bool | None:
            lowered = value.strip().lower()
            if lowered in ("true", "1", "yes", "y", "ja"):
                return True
            if lowered in ("false", "0", "no", "n", "nee"):
                return False
            return None

        name = self.command_name.value.strip()
        if not name:
            await interaction.response.send_message(
                "Command name cannot be empty.", ephemeral=True
            )
            return
        enabled_text = self.enabled.value.strip()
        if not enabled_text:
            await interaction.response.send_message(
                "No changes saved, enabled field was empty.", ephemeral=True
            )
            return
        parsed = parse_bool(enabled_text)
        if parsed is None:
            await interaction.response.send_message(
                "Invalid enabled value, use true/false.", ephemeral=True
            )
            return

        commands_cfg = CONFIG.get("commands")
        if not isinstance(commands_cfg, dict):
            commands_cfg = {}
            CONFIG["commands"] = commands_cfg

        commands_cfg[name] = parsed
        reload_config_state()
        save_config()
        await interaction.response.send_message(
            f"Command '{name}' updated to {'enabled' if parsed else 'disabled'}.",
            ephemeral=True,
        )


class PanelButtonsConfigModal(Modal):
    def __init__(self):
        super().__init__(title="Panel buttons settings")
        self.button_name = TextInput(
            label="Button name",
            required=True,
        )
        self.enabled = TextInput(
            label="Enabled? (true/false)",
            default="true",
            required=False,
        )
        self.add_item(self.button_name)
        self.add_item(self.enabled)

    async def on_submit(self, interaction: discord.Interaction):
        if not isinstance(CONFIG, dict):
            await interaction.response.send_message(
                "Configuration is not a valid dictionary.", ephemeral=True
            )
            return

        def parse_bool(value: str) -> bool | None:
            lowered = value.strip().lower()
            if lowered in ("true", "1", "yes", "y", "ja"):
                return True
            if lowered in ("false", "0", "no", "n", "nee"):
                return False
            return None

        name = self.button_name.value.strip()
        if not name:
            await interaction.response.send_message(
                "Button name cannot be empty.", ephemeral=True
            )
            return
        enabled_text = self.enabled.value.strip()
        if not enabled_text:
            await interaction.response.send_message(
                "No changes saved, enabled field was empty.", ephemeral=True
            )
            return
        parsed = parse_bool(enabled_text)
        if parsed is None:
            await interaction.response.send_message(
                "Invalid enabled value, use true/false.", ephemeral=True
            )
            return

        panel_cfg = CONFIG.get("panel_buttons")
        if not isinstance(panel_cfg, dict):
            panel_cfg = {}
            CONFIG["panel_buttons"] = panel_cfg

        panel_cfg[name] = parsed
        reload_config_state()
        save_config()
        await interaction.response.send_message(
            f"Panel button '{name}' updated to {'enabled' if parsed else 'disabled'}.",
            ephemeral=True,
        )


class ImagesConfigView(View):
    def __init__(self):
        super().__init__(timeout=300)
        self.current_key: str | None = None
        self.message: discord.Message | None = None
        self.add_item(ImagesConfigSelect(self))

    def build_embed(self) -> discord.Embed:
        images_cfg = CONFIG.get("images", {})
        descriptions_cfg = CONFIG.get("image_descriptions", {})
        lines: list[str] = []
        for key, url in sorted(images_cfg.items()):
            prefix = "▶" if key == self.current_key else "•"
            display_url = str(url)
            if len(display_url) > 80:
                display_url = display_url[:77] + "..."
            line = f"{prefix} `{key}` → {display_url}"
            if isinstance(descriptions_cfg, dict):
                desc_value = descriptions_cfg.get(key)
                if isinstance(desc_value, str) and desc_value.strip():
                    line += f"\n   ↳ {desc_value.strip()}"
            lines.append(line)
        if not lines:
            description = (
                "**No images are configured yet.**\n\n"
                "Use the buttons below to add your first image."
            )
        else:
            description = "\n".join(lines)
        embed = discord.Embed(
            title="Image configuration",
            description=description,
            color=discord.Color.blurple(),
        )
        images_cfg = CONFIG.get("images", {})
        descriptions_cfg = CONFIG.get("image_descriptions", {})
        if self.current_key and self.current_key in images_cfg:
            embed.add_field(
                name="Selected key",
                value=self.current_key,
                inline=False,
            )
            current_url = str(images_cfg.get(self.current_key, ""))
            if current_url:
                display_current = (
                    current_url
                    if len(current_url) <= 256
                    else current_url[:253] + "..."
                )
                embed.add_field(
                    name="Current URL",
                    value=display_current,
                    inline=False,
                )
            if isinstance(descriptions_cfg, dict):
                desc_value = descriptions_cfg.get(self.current_key)
                if isinstance(desc_value, str) and desc_value.strip():
                    embed.add_field(
                        name="Command description",
                        value=desc_value.strip(),
                        inline=False,
                    )
        return embed

    async def refresh_message(self):
        if self.message is None:
            return
        embed = self.build_embed()
        await self.message.edit(embed=embed, view=self)

    @discord.ui.button(
        label="Add new image",
        style=discord.ButtonStyle.success,
        row=1,
    )
    async def add_image_button(
        self, interaction: discord.Interaction, button: Button
    ):
        if not has_level_admin_role(interaction.user):
            await interaction.response.send_message(
                "You do not have permission to use this.", ephemeral=True
            )
            return
        modal = AddImageModal(self)
        await interaction.response.send_modal(modal)

    @discord.ui.button(
        label="Change URL of selected image",
        style=discord.ButtonStyle.primary,
        row=1,
    )
    async def edit_image_button(
        self, interaction: discord.Interaction, button: Button
    ):
        if not has_level_admin_role(interaction.user):
            await interaction.response.send_message(
                "You do not have permission to use this.", ephemeral=True
            )
            return
        if not self.current_key:
            await interaction.response.send_message(
                "First select an image from the menu.", ephemeral=True
            )
            return
        images_cfg = CONFIG.get("images", {})
        current_url = ""
        if isinstance(images_cfg, dict):
            current_url = str(images_cfg.get(self.current_key, ""))
        modal = EditImageModal(self.current_key, current_url, self)
        await interaction.response.send_modal(modal)

    @discord.ui.button(
        label="Delete selected image",
        style=discord.ButtonStyle.danger,
        row=2,
    )
    async def delete_image_button(
        self, interaction: discord.Interaction, button: Button
    ):
        if not has_level_admin_role(interaction.user):
            await interaction.response.send_message(
                "You do not have permission to use this.", ephemeral=True
            )
            return
        if not self.current_key:
            await interaction.response.send_message(
                "First select an image from the menu.", ephemeral=True
            )
            return
        images_cfg = CONFIG.get("images")
        if not isinstance(images_cfg, dict):
            await interaction.response.send_message(
                "Configuration is not valid. Please fix config.yml and try again.",
                ephemeral=True,
            )
            return
        key = self.current_key
        if key not in images_cfg:
            await interaction.response.send_message(
                "This image no longer exists in the configuration.",
                ephemeral=True,
            )
            return
        images_cfg.pop(key, None)
        self.current_key = None
        reload_config_state()
        save_config()
        await self.refresh_message()
        await interaction.response.send_message(
            f"Image '{key}' deleted.", ephemeral=True
        )

    @discord.ui.button(
        label="Close",
        style=discord.ButtonStyle.secondary,
        row=2,
    )
    async def close_button(
        self, interaction: discord.Interaction, button: Button
    ):
        for child in self.children:
            child.disabled = True
        if interaction.message:
            await interaction.response.edit_message(view=self)
        else:
            await interaction.response.send_message("Closed.", ephemeral=True)
        self.stop()


class ImagesConfigSelect(discord.ui.Select):
    def __init__(self, view: ImagesConfigView):
        self.view_ref = view
        images_cfg = CONFIG.get("images", {})
        options: list[discord.SelectOption] = []
        if isinstance(images_cfg, dict):
            for key, url in sorted(images_cfg.items()):
                desc = str(url)
                if len(desc) > 90:
                    desc = desc[:87] + "..."
                options.append(
                    discord.SelectOption(
                        label=key,
                        value=key,
                        description=desc or None,
                    )
                )
        if not options:
            options.append(
                discord.SelectOption(
                    label="(no images)",
                    value="__none__",
                    description="Add a new image first.",
                )
            )
        super().__init__(
            placeholder="Choose an image",
            min_values=1,
            max_values=1,
            options=options,
            row=0,
        )

    async def callback(self, interaction: discord.Interaction):
        selected = self.values[0]
        if selected == "__none__":
            self.view_ref.current_key = None
        else:
            self.view_ref.current_key = selected
        embed = self.view_ref.build_embed()
        await interaction.response.edit_message(embed=embed, view=self.view_ref)


class AddImageModal(Modal):
    def __init__(self, parent_view: ImagesConfigView):
        super().__init__(title="New image")
        self.parent_view = parent_view
        self.key_input = TextInput(
            label="Name/key for the image command",
            required=True,
        )
        self.url_input = TextInput(
            label="Image URL",
            required=True,
        )
        self.add_item(self.key_input)
        self.add_item(self.url_input)
        self.description_input = TextInput(
            label="Command description (optional)",
            required=False,
        )
        self.add_item(self.description_input)

    async def on_submit(self, interaction: discord.Interaction):
        if not isinstance(CONFIG, dict):
            await interaction.response.send_message(
                "Configuration is not valid. Please fix config.yml and try again.",
                ephemeral=True,
            )
            return
        images_cfg = CONFIG.get("images")
        if not isinstance(images_cfg, dict):
            images_cfg = {}
            CONFIG["images"] = images_cfg
        key = self.key_input.value.strip()
        url = self.url_input.value.strip()
        if not key or not url:
            await interaction.response.send_message(
                "Name and URL cannot be empty.", ephemeral=True
            )
            return
        is_new = key not in images_cfg
        images_cfg[key] = url

        descriptions_cfg = CONFIG.get("image_descriptions")
        if not isinstance(descriptions_cfg, dict):
            descriptions_cfg = {}
            CONFIG["image_descriptions"] = descriptions_cfg
        desc_raw = self.description_input.value.strip()
        if desc_raw:
            descriptions_cfg[key] = desc_raw

        commands_cfg = CONFIG.get("commands")
        if not isinstance(commands_cfg, dict):
            commands_cfg = {}
            CONFIG["commands"] = commands_cfg
        if is_new and key not in commands_cfg:
            commands_cfg[key] = True

        reload_config_state()
        save_config()

        command_hint = ""
        guild = interaction.guild

        if is_new and guild is not None and is_command_enabled(key):
            async def image_command(cmd_interaction: discord.Interaction):
                image_url = IMAGES.get(key)
                if not image_url:
                    await cmd_interaction.response.send_message(
                        "Image not found.", ephemeral=True
                    )
                    return
                embed = discord.Embed(color=discord.Color.blue())
                embed.set_image(url=image_url)
                await cmd_interaction.response.send_message(embed=embed)

            try:
                cmd_description = descriptions_cfg.get(key) or f"Sends a `{key}` image from the config"
                if len(cmd_description) > 100:
                    cmd_description = cmd_description[:97] + "..."
                new_command = app_commands.Command(
                    name=key,
                    description=cmd_description,
                    callback=image_command,
                )
                bot.tree.add_command(new_command, guild=guild)
                await bot.tree.sync(guild=guild)
                command_hint = f" You can now use `/{key}`."
            except Exception:
                pass

        await self.parent_view.refresh_message()
        message_text = f"Image '{key}' saved.{command_hint}"
        await interaction.response.send_message(message_text, ephemeral=True)


class EditImageModal(Modal):
    def __init__(
        self, key: str, current_url: str, parent_view: ImagesConfigView
    ):
        super().__init__(title=f"Edit URL: {key}")
        self.key = key
        self.parent_view = parent_view
        self.url_input = TextInput(
            label="New image URL",
            default=str(current_url),
            required=True,
        )
        self.add_item(self.url_input)
        descriptions_cfg = CONFIG.get("image_descriptions", {})
        current_desc = ""
        if isinstance(descriptions_cfg, dict):
            raw_desc = descriptions_cfg.get(key, "")
            if isinstance(raw_desc, str):
                current_desc = raw_desc
        self.description_input = TextInput(
            label="Command description (optional)",
            default=str(current_desc),
            required=False,
        )
        self.add_item(self.description_input)

    async def on_submit(self, interaction: discord.Interaction):
        if not isinstance(CONFIG, dict):
            await interaction.response.send_message(
                "Configuration is not valid. Please fix config.yml and try again.",
                ephemeral=True,
            )
            return
        images_cfg = CONFIG.get("images")
        if not isinstance(images_cfg, dict):
            images_cfg = {}
            CONFIG["images"] = images_cfg
        url = self.url_input.value.strip()
        if not url:
            await interaction.response.send_message(
                "URL cannot be empty.", ephemeral=True
            )
            return
        images_cfg[self.key] = url
        descriptions_cfg = CONFIG.get("image_descriptions")
        if not isinstance(descriptions_cfg, dict):
            descriptions_cfg = {}
            CONFIG["image_descriptions"] = descriptions_cfg
        desc_raw = self.description_input.value.strip()
        if desc_raw:
            descriptions_cfg[self.key] = desc_raw
        elif self.key in descriptions_cfg:
            descriptions_cfg.pop(self.key, None)
        reload_config_state()
        save_config()
        await self.parent_view.refresh_message()
        await interaction.response.send_message(
            f"URL for '{self.key}' updated.", ephemeral=True
        )


class CommandsToggleView(View):
    def __init__(self):
        super().__init__(timeout=300)
        self.current_name: str | None = None
        self.message: discord.Message | None = None
        self.add_item(CommandsToggleSelect(self))

    def build_embed(self) -> discord.Embed:
        commands_cfg = CONFIG.get("commands", {})
        lines: list[str] = []
        if isinstance(commands_cfg, dict):
            for name, enabled in sorted(commands_cfg.items()):
                prefix = "✅" if enabled else "❌"
                state_text = "on" if enabled else "off"
                lines.append(f"{prefix} `{name}` → {state_text}")
        if not lines:
            description = (
                "**No commands were found in the configuration.**\n\n"
                "Check `config.yml` under the `commands` section."
            )
        else:
            description = "\n".join(lines)
        embed = discord.Embed(
            title="Commands settings",
            description=description,
            color=discord.Color.blurple(),
        )
        return embed

    async def refresh_message(self):
        if self.message is None:
            return
        embed = self.build_embed()
        await self.message.edit(embed=embed, view=self)

    @discord.ui.button(
        label="Toggle selected command",
        style=discord.ButtonStyle.primary,
        row=1,
    )
    async def toggle_selected_button(
        self, interaction: discord.Interaction, button: Button
    ):
        if not has_level_admin_role(interaction.user):
            await interaction.response.send_message(
                "You do not have permission to use this.", ephemeral=True
            )
            return
        if not self.current_name:
            await interaction.response.send_message(
                "First select a command from the menu.", ephemeral=True
            )
            return
        commands_cfg = CONFIG.get("commands")
        if not isinstance(commands_cfg, dict):
            commands_cfg = {}
            CONFIG["commands"] = commands_cfg
        current = bool(commands_cfg.get(self.current_name, False))
        commands_cfg[self.current_name] = not current
        reload_config_state()
        save_config()
        await self.refresh_message()
        state_text = "enabled" if commands_cfg[self.current_name] else "disabled"
        await interaction.response.send_message(
            f"Command '{self.current_name}' is now {state_text}.",
            ephemeral=True,
        )

    @discord.ui.button(
        label="Close",
        style=discord.ButtonStyle.secondary,
        row=1,
    )
    async def close_button(
        self, interaction: discord.Interaction, button: Button
    ):
        for child in self.children:
            child.disabled = True
        if interaction.message:
            await interaction.response.edit_message(view=self)
        else:
            await interaction.response.send_message("Closed.", ephemeral=True)
        self.stop()


class CommandsToggleSelect(discord.ui.Select):
    def __init__(self, view: CommandsToggleView):
        self.view_ref = view
        commands_cfg = CONFIG.get("commands", {})
        options: list[discord.SelectOption] = []
        if isinstance(commands_cfg, dict):
            for name, enabled in sorted(commands_cfg.items()):
                emoji = "✅" if enabled else "❌"
                desc = "on" if enabled else "off"
                options.append(
                    discord.SelectOption(
                        label=name,
                        value=name,
                        description=desc,
                        emoji=emoji,
                    )
                )
        if not options:
            options.append(
                discord.SelectOption(
                    label="(no commands)",
                    value="__none__",
                    description="No commands found.",
                )
            )
        super().__init__(
            placeholder="Choose a command",
            min_values=1,
            max_values=1,
            options=options,
            row=0,
        )

    async def callback(self, interaction: discord.Interaction):
        selected = self.values[0]
        if selected == "__none__":
            self.view_ref.current_name = None
        else:
            self.view_ref.current_name = selected
        embed = self.view_ref.build_embed()
        await interaction.response.edit_message(embed=embed, view=self.view_ref)


class PanelButtonsToggleView(View):
    def __init__(self):
        super().__init__(timeout=300)
        self.current_name: str | None = None
        self.message: discord.Message | None = None
        self.add_item(PanelButtonsToggleSelect(self))

    def build_embed(self) -> discord.Embed:
        panel_cfg = CONFIG.get("panel_buttons", {})
        lines: list[str] = []
        if isinstance(panel_cfg, dict):
            for name, enabled in sorted(panel_cfg.items()):
                prefix = "✅" if enabled else "❌"
                state_text = "on" if enabled else "off"
                lines.append(f"{prefix} `{name}` → {state_text}")
        if not lines:
            description = (
                "**No panel buttons were found in the configuration.**\n\n"
                "Check `config.yml` under the `panel_buttons` section."
            )
        else:
            description = "\n".join(lines)
        embed = discord.Embed(
            title="Panel buttons settings",
            description=description,
            color=discord.Color.blurple(),
        )
        return embed

    async def refresh_message(self):
        if self.message is None:
            return
        embed = self.build_embed()
        await self.message.edit(embed=embed, view=self)

    @discord.ui.button(
        label="Toggle selected button",
        style=discord.ButtonStyle.primary,
        row=1,
    )
    async def toggle_selected_button(
        self, interaction: discord.Interaction, button: Button
    ):
        if not has_level_admin_role(interaction.user):
            await interaction.response.send_message(
                "You do not have permission to use this.", ephemeral=True
            )
            return
        if not self.current_name:
            await interaction.response.send_message(
                "First select a button from the menu.", ephemeral=True
            )
            return
        panel_cfg = CONFIG.get("panel_buttons")
        if not isinstance(panel_cfg, dict):
            panel_cfg = {}
            CONFIG["panel_buttons"] = panel_cfg
        current = bool(panel_cfg.get(self.current_name, False))
        panel_cfg[self.current_name] = not current
        reload_config_state()
        save_config()
        await self.refresh_message()
        state_text = "enabled" if panel_cfg[self.current_name] else "disabled"
        await interaction.response.send_message(
            f"Panel button '{self.current_name}' is now {state_text}.",
            ephemeral=True,
        )

    @discord.ui.button(
        label="Close",
        style=discord.ButtonStyle.secondary,
        row=1,
    )
    async def close_button(
        self, interaction: discord.Interaction, button: Button
    ):
        for child in self.children:
            child.disabled = True
        if interaction.message:
            await interaction.response.edit_message(view=self)
        else:
            await interaction.response.send_message("Closed.", ephemeral=True)
        self.stop()


class PanelButtonsToggleSelect(discord.ui.Select):
    def __init__(self, view: PanelButtonsToggleView):
        self.view_ref = view
        panel_cfg = CONFIG.get("panel_buttons", {})
        options: list[discord.SelectOption] = []
        if isinstance(panel_cfg, dict):
            for name, enabled in sorted(panel_cfg.items()):
                emoji = "✅" if enabled else "❌"
                desc = "on" if enabled else "off"
                options.append(
                    discord.SelectOption(
                        label=name,
                        value=name,
                        description=desc,
                        emoji=emoji,
                    )
                )
        if not options:
            options.append(
                discord.SelectOption(
                    label="(no buttons)",
                    value="__none__",
                    description="No panel buttons found.",
                )
            )
        super().__init__(
            placeholder="Choose a panel button",
            min_values=1,
            max_values=1,
            options=options,
            row=0,
        )

    async def callback(self, interaction: discord.Interaction):
        selected = self.values[0]
        if selected == "__none__":
            self.view_ref.current_name = None
        else:
            self.view_ref.current_name = selected
        embed = self.view_ref.build_embed()
        await interaction.response.edit_message(embed=embed, view=self.view_ref)


class ServersConfigView(View):
    def __init__(self):
        super().__init__(timeout=300)
        self.current_server: str | None = None
        self.message: discord.Message | None = None
        self.add_item(ServersSelect(self))

    def build_embed(self) -> discord.Embed:
        servers_cfg = CONFIG.get("servers", {})
        lines: list[str] = []
        if isinstance(servers_cfg, dict):
            for name, cfg in sorted(servers_cfg.items()):
                host = ""
                port = ""
                if isinstance(cfg, dict):
                    host = str(cfg.get("host", ""))
                    port = str(cfg.get("port", ""))
                marker = "▶" if name == self.current_server else "•"
                if host and port:
                    lines.append(f"{marker} `{name}` → {host}:{port}")
                elif host:
                    lines.append(f"{marker} `{name}` → {host}")
                else:
                    lines.append(f"{marker} `{name}`")
        if not lines:
            description = (
                "**No servers are configured yet.**\n\n"
                "Use the button below to add your first server."
            )
        else:
            description = "\n".join(lines)
        whitelist_enabled_value = bool(CONFIG.get("whitelist_enabled", True))
        whitelist_text = (
            "enabled ✅" if whitelist_enabled_value else "disabled ❌"
        )
        embed = discord.Embed(
            title="Minecraft server configuration",
            description=description,
            color=discord.Color.blurple(),
        )
        embed.add_field(
            name="Whitelist",
            value=f"The whitelist is currently {whitelist_text}.",
            inline=False,
        )
        if self.current_server and isinstance(servers_cfg, dict):
            cfg = servers_cfg.get(self.current_server, {})
            if isinstance(cfg, dict):
                details: list[str] = []
                details.append(f"Naam: `{self.current_server}`")
                host = cfg.get("host")
                port = cfg.get("port")
                password = cfg.get("password")
                if host:
                    details.append(f"Host: `{host}`")
                if port:
                    details.append(f"RCON-port: `{port}`")
                if password:
                    details.append("Password: set")
                else:
                    details.append("Password: not set")
                embed.add_field(
                    name="Selected server details",
                    value="\n".join(details),
                    inline=False,
                )
        return embed

    async def refresh_message(self):
        if self.message is None:
            return
        embed = self.build_embed()
        await self.message.edit(embed=embed, view=self)

    @discord.ui.button(
        label="Toggle whitelist",
        style=discord.ButtonStyle.primary,
        row=1,
    )
    async def toggle_whitelist_button(
        self, interaction: discord.Interaction, button: Button
    ):
        if not has_level_admin_role(interaction.user):
            await interaction.response.send_message(
                "You do not have permission to use this.", ephemeral=True
            )
            return
        current = bool(CONFIG.get("whitelist_enabled", True))
        new_value = not current
        CONFIG["whitelist_enabled"] = new_value
        reload_config_state()
        save_config()
        await self.refresh_message()
        status = "enabled" if new_value else "disabled"
        await interaction.response.send_message(
            f"The whitelist is now {status}.", ephemeral=True
        )

    @discord.ui.button(
        label="Add new server",
        style=discord.ButtonStyle.success,
        row=1,
    )
    async def add_server_button(
        self, interaction: discord.Interaction, button: Button
    ):
        if not has_level_admin_role(interaction.user):
            await interaction.response.send_message(
                "You do not have permission to use this.", ephemeral=True
            )
            return
        modal = AddServerModal(self)
        await interaction.response.send_modal(modal)

    @discord.ui.button(
        label="Edit selected server",
        style=discord.ButtonStyle.secondary,
        row=2,
    )
    async def edit_server_button(
        self, interaction: discord.Interaction, button: Button
    ):
        if not has_level_admin_role(interaction.user):
            await interaction.response.send_message(
                "You do not have permission to use this.", ephemeral=True
            )
            return
        if not self.current_server:
            await interaction.response.send_message(
                "First select a server from the menu.", ephemeral=True
            )
            return
        servers_cfg = CONFIG.get("servers", {})
        cfg = {}
        if isinstance(servers_cfg, dict):
            cfg = servers_cfg.get(self.current_server, {}) or {}
        host = str(cfg.get("host", "127.0.0.1"))
        port = str(cfg.get("port", 25575))
        password = str(cfg.get("password", ""))
        modal = EditServerModal(self.current_server, host, port, password, self)
        await interaction.response.send_modal(modal)

    @discord.ui.button(
        label="Delete selected server",
        style=discord.ButtonStyle.danger,
        row=2,
    )
    async def delete_server_button(
        self, interaction: discord.Interaction, button: Button
    ):
        if not has_level_admin_role(interaction.user):
            await interaction.response.send_message(
                "You do not have permission to use this.", ephemeral=True
            )
            return
        if not self.current_server:
            await interaction.response.send_message(
                "First select a server from the menu.", ephemeral=True
            )
            return
        servers_cfg = CONFIG.get("servers")
        if not isinstance(servers_cfg, dict):
            await interaction.response.send_message(
                "Configuration is not valid. Please fix config.yml and try again.",
                ephemeral=True,
            )
            return
        name = self.current_server
        if name not in servers_cfg:
            await interaction.response.send_message(
                "This server no longer exists in the configuration.",
                ephemeral=True,
            )
            return
        servers_cfg.pop(name, None)
        self.current_server = None
        reload_config_state()
        save_config()
        await self.refresh_message()
        await interaction.response.send_message(
            f"Server '{name}' deleted.", ephemeral=True
        )

    @discord.ui.button(
        label="Close",
        style=discord.ButtonStyle.secondary,
        row=3,
    )
    async def close_button(
        self, interaction: discord.Interaction, button: Button
    ):
        for child in self.children:
            child.disabled = True
        if interaction.message:
            await interaction.response.edit_message(view=self)
        else:
            await interaction.response.send_message("Closed.", ephemeral=True)
        self.stop()


class ServersSelect(discord.ui.Select):
    def __init__(self, view: ServersConfigView):
        self.view_ref = view
        servers_cfg = CONFIG.get("servers", {})
        options: list[discord.SelectOption] = []
        if isinstance(servers_cfg, dict):
            for name, cfg in sorted(servers_cfg.items()):
                host = ""
                port = ""
                if isinstance(cfg, dict):
                    host = str(cfg.get("host", ""))
                    port = str(cfg.get("port", ""))
                if host and port:
                    desc = f"{host}:{port}"
                elif host:
                    desc = host
                else:
                    desc = ""
                options.append(
                    discord.SelectOption(
                        label=name,
                        value=name,
                        description=desc or None,
                    )
                )
        if not options:
            options.append(
                discord.SelectOption(
                    label="(no servers)",
                    value="__none__",
                    description="Add a new server first.",
                )
            )
        super().__init__(
            placeholder="Choose a server",
            min_values=1,
            max_values=1,
            options=options,
            row=0,
        )

    async def callback(self, interaction: discord.Interaction):
        selected = self.values[0]
        if selected == "__none__":
            self.view_ref.current_server = None
        else:
            self.view_ref.current_server = selected
        embed = self.view_ref.build_embed()
        await interaction.response.edit_message(embed=embed, view=self.view_ref)


class AddServerModal(Modal):
    def __init__(self, parent_view: ServersConfigView):
        super().__init__(title="Add new server")
        self.parent_view = parent_view
        self.name_input = TextInput(
            label="Server name",
            required=True,
        )
        self.host_input = TextInput(
            label="Server host",
            default="127.0.0.1",
            required=True,
        )
        self.port_input = TextInput(
            label="RCON-port",
            default="25575",
            required=True,
        )
        self.password_input = TextInput(
            label="RCON password",
            required=True,
        )
        self.add_item(self.name_input)
        self.add_item(self.host_input)
        self.add_item(self.port_input)
        self.add_item(self.password_input)

    async def on_submit(self, interaction: discord.Interaction):
        if not isinstance(CONFIG, dict):
            await interaction.response.send_message(
                "Configuration is not valid. Please fix config.yml and try again.",
                ephemeral=True,
            )
            return
        name = self.name_input.value.strip()
        host = self.host_input.value.strip()
        port_raw = self.port_input.value.strip()
        password = self.password_input.value.strip()
        if not name or not host or not port_raw or not password:
            await interaction.response.send_message(
                "All fields are required.", ephemeral=True
            )
            return
        servers_cfg = CONFIG.get("servers")
        if not isinstance(servers_cfg, dict):
            servers_cfg = {}
            CONFIG["servers"] = servers_cfg
        if name in servers_cfg:
            await interaction.response.send_message(
                "A server with this name already exists. Use 'Edit selected server' to change it.",
                ephemeral=True,
            )
            return
        try:
            port_value = int(port_raw)
            if port_value <= 0:
                raise ValueError
        except ValueError:
            await interaction.response.send_message(
                "The RCON port must be a positive number.", ephemeral=True
            )
            return
        servers_cfg[name] = {
            "host": host,
            "port": port_value,
            "password": password,
        }
        reload_config_state()
        save_config()
        await self.parent_view.refresh_message()
        await interaction.response.send_message(
            f"Server '{name}' added.", ephemeral=True
        )


class EditServerModal(Modal):
    def __init__(
        self,
        name: str,
        host: str,
        port: str,
        password: str,
        parent_view: ServersConfigView,
    ):
        super().__init__(title=f"Edit server: {name}")
        self.name = name
        self.parent_view = parent_view
        self.host_input = TextInput(
            label="Server host",
            default=str(host),
            required=True,
        )
        self.port_input = TextInput(
            label="RCON-port",
            default=str(port),
            required=True,
        )
        self.password_input = TextInput(
            label="RCON password (leave empty to keep current)",
            default="",
            required=False,
        )
        self.add_item(self.host_input)
        self.add_item(self.port_input)
        self.add_item(self.password_input)

    async def on_submit(self, interaction: discord.Interaction):
        if not isinstance(CONFIG, dict):
            await interaction.response.send_message(
                "Configuration is not valid. Please fix config.yml and try again.",
                ephemeral=True,
            )
            return
        servers_cfg = CONFIG.get("servers")
        if not isinstance(servers_cfg, dict):
            servers_cfg = {}
            CONFIG["servers"] = servers_cfg
        cfg = servers_cfg.get(self.name)
        if not isinstance(cfg, dict):
            cfg = {}
            servers_cfg[self.name] = cfg
        host = self.host_input.value.strip()
        port_raw = self.port_input.value.strip()
        password_raw = self.password_input.value.strip()
        if not host or not port_raw:
            await interaction.response.send_message(
                "Host and port cannot be empty.", ephemeral=True
            )
            return
        try:
            port_value = int(port_raw)
            if port_value <= 0:
                raise ValueError
        except ValueError:
            await interaction.response.send_message(
                "The RCON port must be a positive number.", ephemeral=True
            )
            return
        cfg["host"] = host
        cfg["port"] = port_value
        if password_raw:
            cfg["password"] = password_raw
        reload_config_state()
        save_config()
        await self.parent_view.refresh_message()
        await interaction.response.send_message(
            f"Server '{self.name}' updated.", ephemeral=True
        )


class ConfigSectionSelect(discord.ui.Select):
    def __init__(self, view: "SetupView"):
        self.view_ref = view
        order, comments_map = get_config_template_top_level_info()
        keys: list[str] = []
        allowed_sections = {
            "discord",
            "servers",
            "leveling",
            "roles",
            "messages",
            "images",
            "commands",
            "panel_buttons",
            "moderation",
        }
        if isinstance(CONFIG, dict):
            for k in order:
                if k in CONFIG and k in allowed_sections and k not in keys:
                    keys.append(k)
            for k in CONFIG.keys():
                if k in allowed_sections and k not in keys:
                    keys.append(k)
        options: list[discord.SelectOption] = []
        for key in keys:
            desc = comments_map.get(key, "")
            first_line = desc.split("\n", 1)[0] if desc else ""
            if len(first_line) > 90:
                first_line = first_line[:87] + "..."
            options.append(
                discord.SelectOption(
                    label=key,
                    value=key,
                    description=first_line or None,
                )
            )
        if not options:
            options.append(
                discord.SelectOption(label="config", value="config")
            )
        super().__init__(
            placeholder="Choose a config section",
            min_values=1,
            max_values=1,
            options=options,
            row=2,
        )

    async def callback(self, interaction: discord.Interaction):
        if not has_level_admin_role(interaction.user):
            await interaction.response.send_message(
                "You don't have permission for this.", ephemeral=True
            )
            return
        selected = self.values[0]
        self.view_ref.current_section = selected
        comments_text = get_top_level_comment_text(selected)
        if not comments_text:
            comments_text = "No explanation found for this section."
        if interaction.message and interaction.message.embeds:
            base_embed = interaction.message.embeds[0].copy()
        else:
            base_embed = discord.Embed(
                title="Setup", color=discord.Color.blurple()
            )
        base_embed.title = f"Setup: {selected}"
        parts: list[str] = []
        parts.append(f"**Section:** `{selected}`")
        parts.append("")
        parts.append(comments_text)
        parts.append("")
        if selected in ("commands", "panel_buttons"):
            parts.append(
                "➡️ Use the button below to change what is enabled or disabled."
            )
        else:
            parts.append(
                "➡️ Use the button below to open the settings for this section."
            )
        base_embed.description = "\n".join(parts)
        await interaction.response.edit_message(
            embed=base_embed, view=self.view_ref
        )


async def open_setup_view(interaction: discord.Interaction) -> None:
    guild = interaction.guild
    if guild is None:
        await interaction.response.send_message(
            "This command can only be used in a server.",
            ephemeral=True,
        )
        return

    guild_conf = get_modbot_guild_config(guild.id)
    selected_role_text = None
    if guild_conf.get("mute_role_id"):
        role_obj = guild.get_role(guild_conf["mute_role_id"])
        if role_obj is not None:
            selected_role_text = role_obj.mention
        else:
            selected_role_text = f"Role with ID {guild_conf['mute_role_id']}"
    else:
        selected_role_text = "No mute role selected"

    auto_create_status = (
        "enabled" if guild_conf.get("auto_create_muted_role", False) else "disabled"
    )

    description = (
        "Current settings:\n"
        f"- Mute role: {selected_role_text}\n"
        f"- Automatic mute role creation: {auto_create_status}\n\n"
        "Use the components below to change the settings."
    )

    embed = discord.Embed(
        title="Setup",
        description=description,
        color=discord.Color.blurple(),
    )
    view = SetupView(guild)
    await interaction.response.send_message(embed=embed, view=view, ephemeral=True)


class SetupView(discord.ui.View):
    def __init__(self, guild: discord.Guild):
        super().__init__(timeout=120)
        self.guild = guild
        self.current_section: str | None = None
        self.add_item(ConfigSectionSelect(self))

    @discord.ui.select(
        cls=discord.ui.RoleSelect,
        placeholder="Choose a mute role",
        min_values=0,
        max_values=1,
    )
    async def mute_role_select(self, interaction: discord.Interaction, select: discord.ui.RoleSelect) -> None:
        guild_conf = get_modbot_guild_config(self.guild.id)
        if select.values:
            role = select.values[0]
            guild_conf["mute_role_id"] = role.id
        else:
            guild_conf["mute_role_id"] = None
        save_config()
        await interaction.response.send_message("Mute role updated.", ephemeral=True)

    @discord.ui.button(label="Toggle auto-create mute role", style=discord.ButtonStyle.primary)
    async def toggle_auto_create(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        guild_conf = get_modbot_guild_config(self.guild.id)
        current = guild_conf.get("auto_create_muted_role", False)
        new_value = not current
        guild_conf["auto_create_muted_role"] = new_value
        save_config()
        status = "enabled" if new_value else "disabled"
        await interaction.response.send_message(f"Automatic creation of mute role is now {status}.", ephemeral=True)

    @discord.ui.button(
        label="Edit selected config section",
        style=discord.ButtonStyle.secondary,
        row=3,
    )
    async def edit_config_section(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ) -> None:
        try:
            if not has_level_admin_role(interaction.user):
                await interaction.response.send_message(
                    "You don't have permission for this.", ephemeral=True
                )
                return
            if not self.current_section:
                await interaction.response.send_message(
                    "Select a config section first.", ephemeral=True
                )
                return
            if not isinstance(CONFIG, dict):
                await interaction.response.send_message(
                    "Configuration is not a valid dictionary.", ephemeral=True
                )
                return

            section = self.current_section

            if section == "discord":
                modal = DiscordConfigModal()
                await interaction.response.send_modal(modal)
                return

            if section == "servers":
                view = ServersConfigView()
                embed = view.build_embed()
                await interaction.response.send_message(
                    embed=embed, view=view, ephemeral=True
                )
                try:
                    message = await interaction.original_response()
                    view.message = message
                except Exception:
                    view.message = None
                return

            if section == "leveling":
                view = LevelRolesConfigView(interaction.guild)
                embed = view.build_embed()
                await interaction.response.send_message(
                    embed=embed, view=view, ephemeral=True
                )
                try:
                    message = await interaction.original_response()
                    view.message = message
                except Exception:
                    view.message = None
                return

            if section == "roles":
                modal = RolesConfigModal()
                await interaction.response.send_modal(modal)
                return

            if section == "messages":
                modal = MessagesConfigModal()
                await interaction.response.send_modal(modal)
                return

            if section == "images":
                view = ImagesConfigView()
                embed = view.build_embed()
                await interaction.response.send_message(
                    embed=embed, view=view, ephemeral=True
                )
                try:
                    message = await interaction.original_response()
                    view.message = message
                except Exception:
                    view.message = None
                return

            if section == "moderation":
                view = ModerationConfigView(interaction.user)
                embed = view.build_embed(view.current_category)
                await interaction.response.send_message(
                    embed=embed, view=view, ephemeral=True
                )
                try:
                    message = await interaction.original_response()
                    view.message = message
                except Exception:
                    view.message = None
                return

            if section == "commands":
                view = CommandsToggleView()
                embed = view.build_embed()
                await interaction.response.send_message(
                    embed=embed, view=view, ephemeral=True
                )
                try:
                    message = await interaction.original_response()
                    view.message = message
                except Exception:
                    view.message = None
                return

            if section == "panel_buttons":
                view = PanelButtonsToggleView()
                embed = view.build_embed()
                await interaction.response.send_message(
                    embed=embed, view=view, ephemeral=True
                )
                try:
                    message = await interaction.original_response()
                    view.message = message
                except Exception:
                    view.message = None
                return

            await interaction.response.send_message(
                "This config section cannot be edited from here.", ephemeral=True
            )
        except Exception:
            try:
                error_message = "An error occurred while opening these settings."
                if interaction.response.is_done():
                    await interaction.followup.send(
                        error_message,
                        ephemeral=True,
                    )
                else:
                    await interaction.response.send_message(
                        error_message,
                        ephemeral=True,
                    )
            except Exception:
                pass


if is_command_enabled("setup"):
    @bot.tree.command(name="setup", description="[ADMIN] Configure all settings from config.yml and mute settings")
    @app_commands.default_permissions(administrator=True)
    @app_commands.guild_only()
    async def setup(
        interaction: discord.Interaction,
    ):
        await open_setup_view(interaction)


if is_command_enabled("kick"):
    @bot.tree.command(name="kick", description="Kick a user from the server")
    @app_commands.describe(member="User to kick", reason="Reason for kick")
    @app_commands.default_permissions(kick_members=True)
    @app_commands.guild_only()
    async def kick(
        interaction: discord.Interaction,
        member: discord.Member,
        reason: str = "No reason provided",
    ):
        guild = interaction.guild
        if guild is None:
            await interaction.response.send_message("This command can only be used in a server.", ephemeral=True)
            return
        try:
            description = (
                f"You have been kicked from {guild.name}.\n"
                f"Reason: {reason}\n"
                f"Staff: {interaction.user}"
            )
            await send_punishment_dm(member, guild, "Kick", description)
            await member.kick(reason=reason)
            await interaction.response.send_message(
                f"{member} has been kicked. Reason: {reason}",
                ephemeral=True,
            )
        except discord.Forbidden:
            await interaction.response.send_message("I do not have permission to kick this user.", ephemeral=True)
        except Exception as e:
            await interaction.response.send_message(f"Something went wrong: {e}", ephemeral=True)


if is_command_enabled("ban"):
    @bot.tree.command(name="ban", description="Ban a user from the server")
    @app_commands.describe(
        member="User to ban",
        reason="Reason for ban",
        duration_value="Duration amount for a temporary ban (leave empty for permanent)",
        duration_unit="Time unit for the temporary ban",
    )
    @app_commands.choices(
        duration_unit=[
            app_commands.Choice(name="Seconds", value="seconds"),
            app_commands.Choice(name="Minutes", value="minutes"),
            app_commands.Choice(name="Hours", value="hours"),
            app_commands.Choice(name="Days", value="days"),
            app_commands.Choice(name="Weeks", value="weeks"),
            app_commands.Choice(name="Months", value="months"),
            app_commands.Choice(name="Years", value="years"),
        ]
    )
    @app_commands.default_permissions(ban_members=True)
    @app_commands.guild_only()
    async def ban(
        interaction: discord.Interaction,
        member: discord.Member,
        reason: str = "No reason provided",
        duration_value: app_commands.Range[int, 1, 525600] | None = None,
        duration_unit: app_commands.Choice[str] | None = None,
    ):
        guild = interaction.guild
        if guild is None:
            await interaction.response.send_message("This command can only be used in a server.", ephemeral=True)
            return
        try:
            if (duration_value is None) != (duration_unit is None):
                await interaction.response.send_message(
                    "Please provide both duration value and duration unit, or leave both empty for a permanent ban.",
                    ephemeral=True,
                )
                return

            if duration_value is not None and duration_unit is not None:
                total_seconds, duration_text = get_duration_info(duration_value, duration_unit.value)
                description = (
                    f"You have been temporarily banned from {guild.name}.\n"
                    f"Duration: {duration_text}\n"
                    f"Reason: {reason}\n"
                    f"Staff: {interaction.user}"
                )
                await send_punishment_dm(member, guild, "Temporary ban", description)
                await member.ban(reason=reason)
                log_punishment(
                    guild.id,
                    member.id,
                    "ban_set",
                    {
                        "duration_minutes": total_seconds // 60,
                        "duration_text": duration_text,
                        "reason": reason,
                        "staff_id": interaction.user.id,
                        "temporary": True,
                    },
                )
                asyncio.create_task(schedule_unban(guild.id, member.id, total_seconds))
                await interaction.response.send_message(
                    f"{member} has been temporarily banned for {duration_text}. Reason: {reason}",
                    ephemeral=True,
                )
            else:
                description = (
                    f"You have been permanently banned from {guild.name}.\n"
                    f"Reason: {reason}\n"
                    f"Staff: {interaction.user}"
                )
                await send_punishment_dm(member, guild, "Ban", description)
                await member.ban(reason=reason)
                log_punishment(
                    guild.id,
                    member.id,
                    "ban_set",
                    {
                        "duration_minutes": None,
                        "duration_text": None,
                        "reason": reason,
                        "staff_id": interaction.user.id,
                        "temporary": False,
                    },
                )
                await interaction.response.send_message(
                    f"{member} has been banned. Reason: {reason}",
                    ephemeral=True,
                )
        except discord.Forbidden:
            await interaction.response.send_message("I do not have permission to ban this user.", ephemeral=True)
        except Exception as e:
            await interaction.response.send_message(f"Something went wrong: {e}", ephemeral=True)


class UnbanView(discord.ui.View):
    def __init__(
        self,
        requester: discord.abc.User,
        guild: discord.Guild,
        bans: list[discord.guild.BanEntry],
        reason: str,
    ) -> None:
        super().__init__(timeout=60)
        self.requester = requester
        self.guild = guild
        self.bans = bans
        self.filtered_bans = None
        self.reason = reason
        self.page = 0
        self.page_size = 25
        self.select = discord.ui.Select(placeholder="Choose a user to unban")
        self.refresh_select_options()
        self.select.callback = self.select_callback
        self.add_item(self.select)

    def refresh_select_options(self) -> None:
        source = self.filtered_bans if self.filtered_bans is not None else self.bans
        start = self.page * self.page_size
        end = start + self.page_size
        slice_bans = source[start:end]
        options: list[discord.SelectOption] = []
        for entry in slice_bans:
            label = str(entry.user)
            description = entry.reason[:100] if entry.reason else None
            options.append(
                discord.SelectOption(
                    label=label,
                    value=str(entry.user.id),
                    description=description,
                )
            )
        if not options:
            options.append(
                discord.SelectOption(
                    label="No users on this page",
                    value="none",
                )
            )
        self.select.options = options

    def build_embed(self) -> discord.Embed:
        source = self.filtered_bans if self.filtered_bans is not None else self.bans
        total = len(source)
        if total == 0:
            description = "There are no users on the ban list."
        else:
            total_pages = (total - 1) // self.page_size + 1
            start = self.page * self.page_size
            end = start + self.page_size
            slice_bans = source[start:end]
            lines = []
            for entry in slice_bans:
                lines.append(f"- {entry.user} ({entry.user.id})")
            list_text = "\n".join(lines) if lines else "No users on this page."
            description = f"Page {self.page + 1}/{total_pages}\n\n{list_text}"
        embed = discord.Embed(title="Unban list", description=description, color=discord.Color.blue())
        return embed

    async def select_callback(self, interaction: discord.Interaction) -> None:
        if interaction.user.id != self.requester.id:
            await interaction.response.send_message("Only the requester can use this list.", ephemeral=True)
            return
        if not self.select.values:
            await interaction.response.send_message("Selection is empty.", ephemeral=True)
            return
        value = self.select.values[0]
        if value == "none":
            await interaction.response.send_message("No user is selected.", ephemeral=True)
            return
        try:
            user_id = int(value)
        except ValueError:
            await interaction.response.send_message("Invalid selection.", ephemeral=True)
            return
        try:
            user = await bot.fetch_user(user_id)
        except Exception:
            await interaction.response.send_message("Could not fetch the user.", ephemeral=True)
            return
        try:
            await self.guild.unban(user, reason=self.reason)
            description = (
                f"Your ban in {self.guild.name} has been removed.\n"
                f"Reason: {self.reason}\n"
                f"Staff: {interaction.user}"
            )
            await send_info_dm(user, self.guild, "Unban", description)
            log_punishment(
                self.guild.id,
                user.id,
                "ban_removed",
                {
                    "reason": self.reason,
                    "staff_id": interaction.user.id,
                    "automatic": False,
                },
            )
            await interaction.response.send_message(
                f"{user} has been unbanned. Reason: {self.reason}",
                ephemeral=True,
            )
            self.stop()
        except discord.NotFound:
            await interaction.response.send_message("This user is no longer on the ban list.", ephemeral=True)
        except discord.Forbidden:
            await interaction.response.send_message("I do not have permission to unban.", ephemeral=True)
        except Exception as e:
            await interaction.response.send_message(f"Something went wrong: {e}", ephemeral=True)

    @discord.ui.button(label="Search", style=discord.ButtonStyle.primary)
    async def search(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        if interaction.user.id != self.requester.id:
            await interaction.response.send_message("Only the requester can use this list.", ephemeral=True)
            return
        modal = UnbanSearchModal(self)
        await interaction.response.send_modal(modal)

    @discord.ui.button(label="Previous", style=discord.ButtonStyle.secondary)
    async def previous_page(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        if interaction.user.id != self.requester.id:
            await interaction.response.send_message("Only the requester can use this list.", ephemeral=True)
            return
        source = self.filtered_bans if self.filtered_bans is not None else self.bans
        if self.page > 0 and source:
            self.page -= 1
            self.refresh_select_options()
        await interaction.response.edit_message(embed=self.build_embed(), view=self)

    @discord.ui.button(label="Next", style=discord.ButtonStyle.secondary)
    async def next_page(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        if interaction.user.id != self.requester.id:
            await interaction.response.send_message("Only the requester can use this list.", ephemeral=True)
            return
        source = self.filtered_bans if self.filtered_bans is not None else self.bans
        total = len(source)
        total_pages = (total - 1) // self.page_size + 1
        if self.page + 1 < total_pages:
            self.page += 1
            self.refresh_select_options()
        await interaction.response.edit_message(embed=self.build_embed(), view=self)


class UnbanSearchModal(discord.ui.Modal):
    def __init__(self, view: UnbanView) -> None:
        super().__init__(title="Search in ban list")
        self.view = view
        self.query = discord.ui.TextInput(
            label="Search term",
            placeholder="Search by name, tag or ID",
            required=False,
            max_length=50,
        )
        self.add_item(self.query)

    async def on_submit(self, interaction: discord.Interaction) -> None:
        text = self.query.value.strip().lower()
        if text:
            filtered = []
            for entry in self.view.bans:
                name = str(entry.user)
                name_lower = name.lower()
                if text in name_lower or text in str(entry.user.id):
                    filtered.append(entry)
            self.view.filtered_bans = filtered
        else:
            self.view.filtered_bans = None
        self.view.page = 0
        self.view.refresh_select_options()
        await interaction.response.edit_message(embed=self.view.build_embed(), view=self.view)


class PunishmentHistoryView(discord.ui.View):
    def __init__(self, requester: discord.abc.User, user: discord.Member, events: list[dict]):
        super().__init__(timeout=120)
        self.requester = requester
        self.user = user
        self.events = events
        self.page = 0
        self.page_size = 5

    def format_page_events(self, events_slice: list[dict]) -> str:
        lines = []
        for e in events_slice:
            raw_type = e.get("event_type", "unknown")
            if isinstance(raw_type, int):
                event_type = EVENT_TYPE_NAMES.get(raw_type, "unknown")
            else:
                event_type = str(raw_type)
            ts = e.get("timestamp")
            if isinstance(ts, (int, float)):
                try:
                    dt = datetime.utcfromtimestamp(ts)
                    time_text = dt.strftime("%Y-%m-%d %H:%M:%S UTC")
                except Exception:
                    time_text = "?"
            else:
                time_text = str(ts) if ts is not None else "?"
            reason = e.get("reason")
            if not isinstance(reason, str) or not reason.strip():
                reason = "No reason provided"
            duration_seconds = e.get("duration_seconds")
            staff_id = e.get("staff_id")
            staff_text = f"<@{staff_id}>" if staff_id else "Unknown"
            automatic = e.get("automatic")
            type_text = event_type
            if event_type == "ban_set":
                type_text = "Ban set"
            elif event_type == "ban_removed":
                type_text = "Ban removed"
            elif event_type == "mute_set":
                type_text = "Mute set"
            elif event_type == "mute_removed":
                type_text = "Mute removed"
            elif event_type == "timeout_set":
                type_text = "Timeout set"
            elif event_type == "timeout_removed":
                type_text = "Timeout removed"
            if isinstance(duration_seconds, (int, float)) and duration_seconds > 0:
                seconds_value = int(duration_seconds)
                if seconds_value % 86400 == 0:
                    days = seconds_value // 86400
                    unit = "day" if days == 1 else "days"
                    dur_text = f"{days} {unit}"
                elif seconds_value % 3600 == 0:
                    hours = seconds_value // 3600
                    unit = "hour" if hours == 1 else "hours"
                    dur_text = f"{hours} {unit}"
                elif seconds_value % 60 == 0:
                    minutes_value = seconds_value // 60
                    unit = "minute" if minutes_value == 1 else "minutes"
                    dur_text = f"{minutes_value} {unit}"
                else:
                    dur_text = f"{seconds_value} seconds"
            else:
                dur_text = "n/a"
            automatic_text = ""
            if automatic is True:
                automatic_text = " (automatic)"
            elif automatic is False:
                automatic_text = " (manual)"
            line = (
                f"- [{time_text}] {type_text}{automatic_text}\n"
                f"  Duration: {dur_text} | Staff: {staff_text}\n"
                f"  Reason: {reason}"
            )
            lines.append(line)
        return "\n\n".join(lines) if lines else "No punishment history for this user."

    def build_embed(self) -> discord.Embed:
        total = len(self.events)
        total_pages = (total - 1) // self.page_size + 1
        start = self.page * self.page_size
        end = start + self.page_size
        slice_events = self.events[start:end]
        description = self.format_page_events(slice_events)
        embed = discord.Embed(
            title=f"History for {self.user}",
            description=description,
            color=discord.Color.orange(),
        )
        embed.set_footer(text=f"Page {self.page + 1}/{total_pages} • {total} events total")
        return embed

    async def ensure_author(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.requester.id:
            await interaction.response.send_message(
                "You cannot control this history view.", ephemeral=True
            )
            return False
        return True

    @discord.ui.button(label="Previous", style=discord.ButtonStyle.secondary)
    async def previous_page(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not await self.ensure_author(interaction):
            return
        if self.page == 0:
            await interaction.response.defer()
            return
        self.page -= 1
        await interaction.response.edit_message(embed=self.build_embed(), view=self)

    @discord.ui.button(label="Next", style=discord.ButtonStyle.secondary)
    async def next_page(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not await self.ensure_author(interaction):
            return
        total = len(self.events)
        total_pages = (total - 1) // self.page_size + 1
        if self.page + 1 >= total_pages:
            await interaction.response.defer()
            return
        self.page += 1
        await interaction.response.edit_message(embed=self.build_embed(), view=self)

if is_command_enabled("unban"):
    @bot.tree.command(name="unban", description="Unban a user via a list")
    @app_commands.describe(reason="Reason")
    @app_commands.default_permissions(ban_members=True)
    @app_commands.guild_only()
    async def unban(
        interaction: discord.Interaction,
        reason: str = "No reason provided",
    ):
        guild = interaction.guild
        if guild is None:
            await interaction.response.send_message("This command can only be used in a server.", ephemeral=True)
            return
        await interaction.response.defer(ephemeral=True)
        try:
            bans = [entry async for entry in guild.bans()]
            if not bans:
                await interaction.followup.send("There are no users on the ban list.", ephemeral=True)
                return
            view = UnbanView(interaction.user, guild, bans, reason)
            await interaction.followup.send(
                "Choose a user to unban.",
                embed=view.build_embed(),
                view=view,
                ephemeral=True,
            )
        except discord.Forbidden:
            await interaction.followup.send("I do not have permission to retrieve the ban list.", ephemeral=True)
        except Exception as e:
            await interaction.followup.send(f"Something went wrong: {e}", ephemeral=True)


if is_command_enabled("clear"):
    @bot.tree.command(name="clear", description="Delete messages in a channel")
    @app_commands.describe(amount="Number of messages to delete (max 100)")
    @app_commands.default_permissions(manage_messages=True)
    @app_commands.guild_only()
    async def clear(
        interaction: discord.Interaction,
        amount: app_commands.Range[int, 1, 100],
    ):
        channel = interaction.channel
        if not isinstance(channel, (discord.TextChannel, discord.Thread)):
            await interaction.response.send_message("This can only be used in text channels.", ephemeral=True)
            return

        await interaction.response.defer(ephemeral=True)
        try:
            deleted = await channel.purge(limit=amount)
            await interaction.followup.send(f"Deleted {len(deleted)} messages.", ephemeral=True)
        except discord.Forbidden:
            await interaction.followup.send("I do not have permission to delete messages.", ephemeral=True)
        except Exception as e:
            await interaction.followup.send(f"Something went wrong: {e}", ephemeral=True)


if is_command_enabled("violations"):
    @bot.tree.command(name="violations", description="[ADMIN] View a user's warnings and history")
    @app_commands.describe(
        user="The user whose warnings you want to see"
    )
    async def violations_command(interaction: discord.Interaction, user: discord.Member):
        if not has_level_admin_role(interaction.user):
            await interaction.response.send_message(
                f"❌ You need the '{LEVEL_ADMIN_ROLE}' role to use this command.",
                ephemeral=True,
            )
            return

        user_id = str(user.id)
        if user_id not in levels:
            await interaction.response.send_message(
                f"No leveling or warning data found for {user.mention}.",
                ephemeral=True,
            )
            return

        ensure_user_schema(user_id)
        data = levels[user_id]
        violations_data = data.get("violations", {})

        if not violations_data:
            description = f"{user.mention} currently has no recorded warnings."
        else:
            lines = []
            for category_name, count in violations_data.items():
                category_cfg = MODERATION_CATEGORIES.get(category_name, {})
                max_violations = int(category_cfg.get("max_violations", 1))
                timeout_days = float(category_cfg.get("timeout_days", 0))
                timeout_text = (
                    f"{timeout_days} days timeout"
                    if timeout_days > 0 and max_violations > 0
                    else "No automatic timeout"
                )
                lines.append(
                    f"• {category_name}: {count}/{max_violations} ({timeout_text})"
                )
            description = "\n".join(lines)

        embed = discord.Embed(
            title=f"Warnings for {user.display_name}",
            color=discord.Color.orange(),
            description=description,
        )
        embed.add_field(name="Level", value=data.get("level", 0), inline=True)
        embed.add_field(
            name="Unique messages", value=data.get("unique_count", 0), inline=True
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)
        guild = interaction.guild
        if guild is not None:
            key = str(guild.id)
            all_events = punishments.get(key, [])
            user_events = [e for e in all_events if e.get("user_id") == user.id]
            if user_events:
                def _event_timestamp(entry: dict) -> float:
                    ts = entry.get("timestamp")
                    if isinstance(ts, (int, float)):
                        return float(ts)
                    if isinstance(ts, str):
                        try:
                            return datetime.fromisoformat(ts).timestamp()
                        except Exception:
                            return 0.0
                    return 0.0

                user_events = sorted(user_events, key=_event_timestamp, reverse=True)
                view = PunishmentHistoryView(interaction.user, user, user_events)
                history_embed = view.build_embed()
                await interaction.followup.send(
                    embed=history_embed,
                    view=view,
                    ephemeral=True,
                )


if is_command_enabled("warnings"):
    @bot.tree.command(name="warnings", description="[ADMIN] Manage a user's warnings")
    @app_commands.describe(
        user="The user whose warnings you want to manage"
    )
    async def warnings_command(interaction: discord.Interaction, user: discord.Member):
        if not has_level_admin_role(interaction.user):
            await interaction.response.send_message(
                f"❌ You need the '{LEVEL_ADMIN_ROLE}' role to use this command.",
                ephemeral=True,
            )
            return

        user_id = str(user.id)
        if user_id not in levels:
            await interaction.response.send_message(
                f"No leveling or warning data found for {user.mention}.",
                ephemeral=True,
            )
            return

        ensure_user_schema(user_id)
        data = levels[user_id]
        violations_data = data.get("violations", {})

        if not isinstance(violations_data, dict) or not violations_data:
            await interaction.response.send_message(
                f"{user.mention} currently has no recorded warnings.",
                ephemeral=True,
            )
            return

        view = UserViolationsView(interaction.user, user)
        embed = view.build_embed()
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)


if is_command_enabled("clearwarnings"):
    @bot.tree.command(name="clearwarnings", description="[ADMIN] Clear warnings for a user")
    @app_commands.describe(
        user="The user whose warnings you want to clear",
        category="Optional: category to clear (empty = all)",
    )
    async def clearwarnings_command(
        interaction: discord.Interaction,
        user: discord.Member,
        category: str | None = None,
    ):
        if not has_level_admin_role(interaction.user):
            await interaction.response.send_message(
                f"❌ You need the '{LEVEL_ADMIN_ROLE}' role to use this command.",
                ephemeral=True,
            )
            return

        user_id = str(user.id)
        if user_id not in levels:
            await interaction.response.send_message(
                f"No leveling or warning data found for {user.mention}.",
                ephemeral=True,
            )
            return

        ensure_user_schema(user_id)
        data = levels[user_id]
        violations_data = data.get("violations", {})

        if not violations_data:
            await interaction.response.send_message(
                f"{user.mention} currently has no recorded warnings.",
                ephemeral=True,
            )
            return

        if category and category.strip():
            category_name = category.strip()
            if category_name not in violations_data:
                await interaction.response.send_message(
                    f"{user.mention} has no warnings in category '{category_name}'.",
                    ephemeral=True,
                )
                return

            del violations_data[category_name]
            levels[user_id]["violations"] = violations_data
            save_levels()

            await interaction.response.send_message(
                f"Warnings for {user.mention} in category '{category_name}' have been cleared.",
                ephemeral=True,
            )
            return

        levels[user_id]["violations"] = {}
        save_levels()

        await interaction.response.send_message(
            f"All warnings for {user.mention} have been cleared.",
            ephemeral=True,
        )

if is_command_enabled("fixroles"):
    @bot.tree.command(name="fixroles", description="[ADMIN] Fix role assignments for all members")
    @app_commands.default_permissions(administrator=True)
    async def fixroles_command(interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        count = 0
        for member in interaction.guild.members:
            if member.bot:
                continue
                
            user_id = str(member.id)
            if user_id in levels:
                current_level = levels[user_id]["level"]
                await bot.ensure_correct_roles(member, current_level)
                count += 1
        
        await interaction.followup.send(f"Verified roles for {count} members!", ephemeral=True)

@bot.tree.command(name="setlevel", description="[ADMIN] Set a user's level")
@app_commands.describe(
    user="The user to set level for",
    level="The level to set"
)
async def setlevel_command(interaction: discord.Interaction, user: discord.Member, level: int):
    if not has_level_admin_role(interaction.user):
        await interaction.response.send_message(
            f"❌ You need the '{LEVEL_ADMIN_ROLE}' role to use this command!",
            ephemeral=True
        )
        return
        
    if MAX_LEVEL_ROLE > 0:
        if level < 1 or level > MAX_LEVEL_ROLE:
            await interaction.response.send_message(
                f"❌ Level must be between 1 and {MAX_LEVEL_ROLE}!",
                ephemeral=True
            )
            return
    else:
        if level < 1:
            await interaction.response.send_message(
                "❌ Level must be at least 1!",
                ephemeral=True
            )
            return
        
    user_id = str(user.id)
    
    if user_id not in levels:
        join_date = user.joined_at.timestamp() if user.joined_at else time.time()
        levels[user_id] = {
            "level": 0,
            "unique_count": 0,
            "recent_hashes": [],
            "last_message_time": 0,
            "join_date": int(join_date)
        }
    else:
        ensure_user_schema(user_id)
    
    # Get current status
    old_level = levels[user_id]["level"]
    
    # Set new level
    levels[user_id]["level"] = level
    
    required_uniques = required_uniques_for_level(level)
    if levels[user_id].get("unique_count", 0) < required_uniques:
        levels[user_id]["unique_count"] = required_uniques
    
    # Update roles
    await bot.ensure_correct_roles(user, level)
    save_levels()
    
    # Create embed response
    embed = discord.Embed(
        title="✅ Level Updated",
        color=discord.Color.green(),
        description=f"{user.mention}'s level has been updated by {interaction.user.mention}"
    )
    embed.add_field(name="Previous Level", value=old_level, inline=True)
    embed.add_field(name="New Level", value=level, inline=True)
    
    role_id = LEVEL_ROLES.get(level)
    if role_id:
        role = interaction.guild.get_role(role_id)
        if role:
            embed.add_field(name="Assigned Role", value=role.mention, inline=False)
    
    await interaction.response.send_message(embed=embed)

if __name__ == "__main__":
    bot.run(TOKEN)
