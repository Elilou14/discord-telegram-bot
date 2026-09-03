#!/usr/bin/env node
/**
 * Registers the slash commands with Discord. Run once after adding
 * or changing a command (Discord caches the definitions on their
 * end, not this process's). With DISCORD_GUILD_ID set, commands
 * register instantly to that one server -- handy while developing,
 * since global commands can take up to an hour to propagate.
 */

import { REST, Routes } from "discord.js";

import { commands } from "./commands.js";

try {
  process.loadEnvFile();
} catch {
  // .env is optional -- production can set real env vars directly.
}

const rest = new REST().setToken(process.env.DISCORD_TOKEN);
const body = commands.map((c) => c.data.toJSON());

const route = process.env.DISCORD_GUILD_ID
  ? Routes.applicationGuildCommands(process.env.DISCORD_CLIENT_ID, process.env.DISCORD_GUILD_ID)
  : Routes.applicationCommands(process.env.DISCORD_CLIENT_ID);

const result = await rest.put(route, { body });
console.log(`${result.length} commande(s) enregistree(s).`);
