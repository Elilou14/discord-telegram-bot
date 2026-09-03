/**
 * Reads moderation config from environment variables, with sane
 * defaults. Pure given an env object, so it's testable without
 * touching real process.env.
 */
export function loadModerationConfig(env = process.env) {
  const bannedWords = (env.BANNED_WORDS ?? "")
    .split(",")
    .map((word) => word.trim())
    .filter(Boolean);

  return {
    bannedWords,
    flood: {
      maxMessages: Number(env.FLOOD_MAX_MESSAGES) || 5,
      windowMs: Number(env.FLOOD_WINDOW_MS) || 10_000,
    },
    warnThresholds: {
      mute: Number(env.WARN_MUTE_THRESHOLD) || 3,
      kick: Number(env.WARN_KICK_THRESHOLD) || 5,
    },
  };
}
