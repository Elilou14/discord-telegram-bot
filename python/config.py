"""
Reads moderation config from environment variables, with sane
defaults. Pure given an env mapping, so it's testable without
touching real environment variables. Mirrors node/config.js.
"""

import os


def _int_env(env, key, default):
    value = env.get(key)
    if value is None or value == "":
        return default
    try:
        return int(value)
    except ValueError:
        return default


def load_moderation_config(env=None):
    env = os.environ if env is None else env

    banned_words = [word.strip() for word in env.get("BANNED_WORDS", "").split(",") if word.strip()]

    return {
        "banned_words": banned_words,
        "flood": {
            "max_messages": _int_env(env, "FLOOD_MAX_MESSAGES", 5),
            "window_ms": _int_env(env, "FLOOD_WINDOW_MS", 10_000),
        },
        "warn_thresholds": {
            "mute": _int_env(env, "WARN_MUTE_THRESHOLD", 3),
            "kick": _int_env(env, "WARN_KICK_THRESHOLD", 5),
        },
    }
