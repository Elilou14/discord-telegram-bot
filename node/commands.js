/**
 * Slash command definitions + handlers. Each command's `execute`
 * receives the interaction and a shared, mutable `ctx` (in-memory
 * state kept in sync with SQLite, plus config and the question
 * bank) -- see bot.js for how ctx is built. The rules themselves
 * (validation, scoring, flood/word checks) all live in the pure
 * *-logic.js modules; this file is just wiring.
 */

import { PermissionFlagsBits, SlashCommandBuilder } from "discord.js";

import {
  buildQuizComponents,
  buildQuizEmbed,
  formatReminderFired,
  formatReminderList,
  formatStandings,
} from "./discord-format.js";
import { recommendedAction, addWarning, warningCount } from "./moderation-logic.js";
import { insertWarning } from "./moderation-store.js";
import { activeRemindersForUser, cancelReminder, createReminder, parseDuration } from "./reminders-logic.js";
import { deleteReminder, insertReminder } from "./reminders-store.js";
import { advanceQuestion, currentQuestion, pickQuestions, standings, startSession } from "./quiz-logic.js";

const QUESTION_DURATION_MS = 15_000;
const QUIZ_QUESTION_COUNT = 5;

async function runQuizRound(channel, ctx, sessionId) {
  const session = ctx.quizSessions.get(sessionId);
  if (!session) return; // cancelled or superseded

  const question = currentQuestion(session);
  if (!question) {
    const finalStandings = standings(session);
    await channel.send({
      content: `Quiz termine ! Classement :\n${formatStandings(finalStandings, (id) => `<@${id}>`)}`,
    });
    ctx.quizSessions.delete(sessionId);
    return;
  }

  const message = await channel.send({
    embeds: [buildQuizEmbed(question, session.currentIndex, session.questions.length)],
    components: buildQuizComponents(question, sessionId),
  });

  setTimeout(async () => {
    const latest = ctx.quizSessions.get(sessionId);
    if (!latest) return; // session ended early
    try {
      await message.edit({ components: [] });
      await channel.send(`Bonne reponse : **${question.choices[question.answerIndex]}**`);
    } catch {
      // message may have been deleted; nothing to clean up
    }
    ctx.quizSessions.set(sessionId, advanceQuestion(latest));
    await runQuizRound(channel, ctx, sessionId);
  }, QUESTION_DURATION_MS);
}

export const commands = [
  {
    data: new SlashCommandBuilder()
      .setName("remind")
      .setDescription("Programme un rappel.")
      .addStringOption((opt) =>
        opt.setName("quand").setDescription("Ex: 10m, 2h, 1d, ou 2026-09-10 14:30").setRequired(true)
      )
      .addStringOption((opt) => opt.setName("message").setDescription("Le message du rappel").setRequired(true)),
    async execute(interaction, ctx) {
      try {
        const reminder = createReminder({
          userId: interaction.user.id,
          channelId: interaction.channelId,
          guildId: interaction.guildId,
          message: interaction.options.getString("message"),
          when: interaction.options.getString("quand"),
        });
        insertReminder(ctx.reminderDb, reminder);
        ctx.reminders.push(reminder);
        await interaction.reply({
          content: `Rappel programme pour <t:${Math.floor(reminder.dueAt / 1000)}:F>.`,
          ephemeral: true,
        });
      } catch (err) {
        await interaction.reply({ content: `Erreur : ${err.message}`, ephemeral: true });
      }
    },
  },
  {
    data: new SlashCommandBuilder().setName("remind-list").setDescription("Liste vos rappels actifs."),
    async execute(interaction, ctx) {
      const active = activeRemindersForUser(ctx.reminders, interaction.user.id);
      await interaction.reply({ content: formatReminderList(active), ephemeral: true });
    },
  },
  {
    data: new SlashCommandBuilder()
      .setName("remind-cancel")
      .setDescription("Annule un rappel.")
      .addStringOption((opt) =>
        opt.setName("id").setDescription("Les 8 premiers caracteres de l'id (voir /remind-list)").setRequired(true)
      ),
    async execute(interaction, ctx) {
      const shortId = interaction.options.getString("id");
      const match = activeRemindersForUser(ctx.reminders, interaction.user.id).find((r) => r.id.startsWith(shortId));
      if (!match) {
        await interaction.reply({ content: "Rappel introuvable.", ephemeral: true });
        return;
      }
      ctx.reminders = cancelReminder(ctx.reminders, match.id, interaction.user.id);
      deleteReminder(ctx.reminderDb, match.id);
      await interaction.reply({ content: "Rappel annule.", ephemeral: true });
    },
  },
  {
    data: new SlashCommandBuilder()
      .setName("quiz")
      .setDescription("Demarre un quiz dans ce salon.")
      .addStringOption((opt) => opt.setName("categorie").setDescription("Categorie (optionnel)").setRequired(false)),
    async execute(interaction, ctx) {
      if (ctx.quizSessions.has(interaction.channelId)) {
        await interaction.reply({ content: "Un quiz est deja en cours dans ce salon.", ephemeral: true });
        return;
      }
      const category = interaction.options.getString("categorie");
      const questions = pickQuestions(ctx.questionBank, QUIZ_QUESTION_COUNT, { category });
      if (questions.length === 0) {
        await interaction.reply({ content: `Aucune question pour la categorie "${category}".`, ephemeral: true });
        return;
      }

      const session = startSession({ channelId: interaction.channelId, questions });
      ctx.quizSessions.set(interaction.channelId, session);
      await interaction.reply(`Quiz lance : ${questions.length} questions, ${QUESTION_DURATION_MS / 1000}s chacune !`);
      await runQuizRound(interaction.channel, ctx, interaction.channelId);
    },
  },
  {
    data: new SlashCommandBuilder()
      .setName("warn")
      .setDescription("Avertit un membre.")
      .addUserOption((opt) => opt.setName("membre").setDescription("Le membre a avertir").setRequired(true))
      .addStringOption((opt) => opt.setName("raison").setDescription("Raison de l'avertissement").setRequired(true))
      .setDefaultMemberPermissions(PermissionFlagsBits.ModerateMembers),
    async execute(interaction, ctx) {
      const target = interaction.options.getUser("membre");
      const reason = interaction.options.getString("raison");

      ctx.warnings = addWarning(ctx.warnings, { userId: target.id, moderatorId: interaction.user.id, reason });
      const lastWarning = ctx.warnings[ctx.warnings.length - 1];
      insertWarning(ctx.moderationDb, lastWarning);

      const count = warningCount(ctx.warnings, target.id);
      const action = recommendedAction(count, ctx.config.warnThresholds);

      let followUp = "";
      if (action === "mute") followUp = " Ce membre a atteint le seuil de mute recommande.";
      if (action === "kick") followUp = " Ce membre a atteint le seuil d'exclusion recommande.";

      await interaction.reply(`<@${target.id}> a ete averti (${count} avertissement${count > 1 ? "s" : ""}).${followUp}`);
    },
  },
  {
    data: new SlashCommandBuilder()
      .setName("mute")
      .setDescription("Reduit un membre au silence temporairement.")
      .addUserOption((opt) => opt.setName("membre").setDescription("Le membre a mute").setRequired(true))
      .addStringOption((opt) => opt.setName("duree").setDescription("Ex: 10m, 1h").setRequired(true))
      .setDefaultMemberPermissions(PermissionFlagsBits.ModerateMembers),
    async execute(interaction, ctx) {
      const { parseDuration } = await import("./reminders-logic.js");
      const durationMs = parseDuration(interaction.options.getString("duree"));
      if (durationMs === null) {
        await interaction.reply({ content: "Duree invalide (ex: 10m, 1h).", ephemeral: true });
        return;
      }
      const member = await interaction.guild.members.fetch(interaction.options.getUser("membre").id);
      await member.timeout(durationMs, "Mute via /mute");
      await interaction.reply(`<@${member.id}> est reduit au silence pour ${interaction.options.getString("duree")}.`);
    },
  },
  {
    data: new SlashCommandBuilder()
      .setName("clear")
      .setDescription("Supprime les N derniers messages de ce salon.")
      .addIntegerOption((opt) =>
        opt.setName("nombre").setDescription("Nombre de messages (1-100)").setRequired(true).setMinValue(1).setMaxValue(100)
      )
      .setDefaultMemberPermissions(PermissionFlagsBits.ManageMessages),
    async execute(interaction) {
      const count = interaction.options.getInteger("nombre");
      const deleted = await interaction.channel.bulkDelete(count, true);
      await interaction.reply({ content: `${deleted.size} message(s) supprime(s).`, ephemeral: true });
    },
  },
];
