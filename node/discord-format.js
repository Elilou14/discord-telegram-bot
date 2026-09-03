/**
 * Discord message/embed/component builders and plain-text
 * formatting. discord.js's builders (EmbedBuilder, ButtonBuilder,
 * ActionRowBuilder) are pure data structures -- building one doesn't
 * touch the network -- so this whole module is testable via
 * `.toJSON()` without a live bot connection.
 */

import { ActionRowBuilder, ButtonBuilder, ButtonStyle, EmbedBuilder } from "discord.js";

const CHOICE_LETTERS = ["A", "B", "C", "D"];

export function buildQuizEmbed(question, index, total) {
  return new EmbedBuilder()
    .setTitle(`Question ${index + 1}/${total}`)
    .setDescription(question.question)
    .addFields(question.choices.map((choice, i) => ({ name: CHOICE_LETTERS[i], value: choice, inline: true })))
    .setColor(0x5865f2);
}

export function buildQuizComponents(question, sessionId) {
  const row = new ActionRowBuilder().addComponents(
    question.choices.map((_choice, i) =>
      new ButtonBuilder()
        .setCustomId(`quiz:${sessionId}:${i}`)
        .setLabel(CHOICE_LETTERS[i])
        .setStyle(ButtonStyle.Primary)
    )
  );
  return [row];
}

export function formatReminderFired(reminder) {
  return `<@${reminder.userId}> :alarm_clock: Rappel : ${reminder.message}`;
}

export function formatReminderList(reminders) {
  if (reminders.length === 0) return "Vous n'avez aucun rappel actif.";
  return reminders
    .map((r, i) => `${i + 1}. <t:${Math.floor(r.dueAt / 1000)}:R> -- ${r.message} (id: \`${r.id.slice(0, 8)}\`)`)
    .join("\n");
}

export function formatStandings(standingsList, resolveDisplayName) {
  if (standingsList.length === 0) return "Personne n'a encore marque de points.";
  return standingsList
    .map((s, i) => `${i + 1}. ${resolveDisplayName(s.userId)} -- ${s.score} pt${s.score > 1 ? "s" : ""}`)
    .join("\n");
}
