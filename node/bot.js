#!/usr/bin/env node
/**
 * Discord bot entry point: wires the client to the pure logic
 * modules through a single shared, mutable `ctx` (in-memory state
 * kept in sync with SQLite). Run `node deploy-commands.js` once
 * before starting this, so Discord knows about the slash commands.
 */

import { readFileSync } from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

import { Client, Events, GatewayIntentBits } from "discord.js";

import { commands } from "./commands.js";
import { loadModerationConfig } from "./config.js";
import { evaluateMessage } from "./moderation-logic.js";
import { loadAllWarnings, openModerationStore } from "./moderation-store.js";
import { submitAnswer } from "./quiz-logic.js";
import { loadAllReminders, openStore as openReminderStore } from "./reminders-store.js";
import { startReminderScheduler } from "./scheduler.js";

try {
  process.loadEnvFile();
} catch {
  // .env is optional -- production can set real env vars directly.
}

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const questionBank = JSON.parse(readFileSync(path.join(__dirname, "data", "questions.json"), "utf8"));

const ctx = {
  config: loadModerationConfig(),
  questionBank,
  reminderDb: openReminderStore(path.join(__dirname, "reminders.sqlite")),
  moderationDb: openModerationStore(path.join(__dirname, "moderation.sqlite")),
  quizSessions: new Map(),
  recentMessageTimestamps: new Map(), // userId -> number[]
};
ctx.reminders = loadAllReminders(ctx.reminderDb);
ctx.warnings = loadAllWarnings(ctx.moderationDb);

const client = new Client({
  intents: [GatewayIntentBits.Guilds, GatewayIntentBits.GuildMessages, GatewayIntentBits.MessageContent],
});

client.once(Events.ClientReady, (readyClient) => {
  console.log(`Connecte en tant que ${readyClient.user.tag}`);
  startReminderScheduler(client, ctx);
});

client.on(Events.InteractionCreate, async (interaction) => {
  if (interaction.isChatInputCommand()) {
    const command = commands.find((c) => c.data.name === interaction.commandName);
    if (!command) return;
    try {
      await command.execute(interaction, ctx);
    } catch (err) {
      console.error(err);
      const payload = { content: "Une erreur est survenue.", ephemeral: true };
      if (interaction.replied || interaction.deferred) await interaction.followUp(payload);
      else await interaction.reply(payload);
    }
    return;
  }

  if (interaction.isButton() && interaction.customId.startsWith("quiz:")) {
    const [, sessionId, choiceIndexStr] = interaction.customId.split(":");
    const session = ctx.quizSessions.get(sessionId);
    if (!session) {
      await interaction.reply({ content: "Ce quiz est termine.", ephemeral: true });
      return;
    }
    const { session: nextSession, status } = submitAnswer(session, interaction.user.id, Number(choiceIndexStr));
    ctx.quizSessions.set(sessionId, nextSession);

    const messages = {
      correct: "Bonne reponse !",
      incorrect: "Mauvaise reponse.",
      "already-answered": "Vous avez deja repondu a cette question.",
      complete: "Ce quiz est termine.",
    };
    await interaction.reply({ content: messages[status], ephemeral: true });
  }
});

client.on(Events.MessageCreate, async (message) => {
  if (message.author.bot) return;

  const timestamps = ctx.recentMessageTimestamps.get(message.author.id) ?? [];
  const verdict = evaluateMessage({
    text: message.content,
    timestamp: message.createdTimestamp,
    recentTimestamps: timestamps,
    bannedWords: ctx.config.bannedWords,
    floodOptions: ctx.config.flood,
  });
  ctx.recentMessageTimestamps.set(message.author.id, [...timestamps, message.createdTimestamp].slice(-20));

  if (verdict.action === "delete") {
    await message.delete().catch(() => {});
    await message.channel.send(`<@${message.author.id}>, message supprime (mot interdit).`);
  } else if (verdict.action === "mute" && message.member) {
    await message.member.timeout(60_000, "Flood detecte").catch(() => {});
    await message.channel.send(`<@${message.author.id}> a ete mis en pause 1 minute (flood detecte).`);
  }
});

client.login(process.env.DISCORD_TOKEN);
