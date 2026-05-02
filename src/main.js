import "dotenv/config";
import { spawn } from "child_process";
import { Client, GatewayIntentBits } from "discord.js";
import { append, ensureMemoryDir, read, remember, search, todayFile, write } from "./memory.js";
import { heartbeat, tierIntervalMinutes } from "./heartbeat.js";

const args = process.argv.slice(2);
const root = process.env.RECLAW_HOME || process.cwd();
const agentName = process.env.AGENT_NAME || "ReClaw";
const intervalMinutes = Number(process.env.HEARTBEAT_INTERVAL || tierIntervalMinutes());

function argValue(flag) {
  const index = args.indexOf(flag);
  return index >= 0 ? args[index + 1] : null;
}

async function loadIdentity() {
  const files = ["SOUL.md", "USER.md", "DIRECTIVE.md", "AGENTS.md"];
  const chunks = [];
  for (const file of files) {
    try {
      chunks.push(`# ${file}\n${await readFileFromRoot(file)}`);
    } catch {
      chunks.push(`# ${file}\nNot configured yet.`);
    }
  }
  return chunks.join("\n\n");
}

async function readFileFromRoot(file) {
  const fs = await import("fs/promises");
  return fs.readFile(new URL(file, `file://${root.endsWith("/") ? root : `${root}/`}`), "utf8");
}

function runClaude(prompt, system) {
  if (process.env.RECLAW_TEST_MODE === "true") {
    return Promise.resolve(`${agentName} received: ${prompt}`);
  }

  return new Promise((resolve, reject) => {
    const child = spawn("claude", [
      "-p",
      "--output-format",
      "text",
      "--append-system-prompt",
      system,
      prompt,
    ], { cwd: root, env: process.env });

    let stdout = "";
    let stderr = "";
    child.stdout.on("data", (data) => { stdout += data; });
    child.stderr.on("data", (data) => { stderr += data; });
    child.on("error", reject);
    child.on("close", (code) => {
      if (code === 0 && stdout.trim()) return resolve(stdout.trim());
      reject(new Error(stderr.trim() || `claude exited with code ${code}`));
    });
  });
}

async function respondToMessage(content) {
  const system = await loadIdentity();
  const reply = await runClaude(content, system);
  await append(todayFile(), `\n- ${new Date().toISOString()} message: ${content}\n  reply: ${reply}\n`);
  return reply;
}

async function connectDiscord() {
  const token = process.env.DISCORD_BOT_TOKEN;
  if (!token) {
    console.log("[reclaw] Discord not configured; running in console mode");
    return null;
  }

  const client = new Client({
    intents: [
      GatewayIntentBits.Guilds,
      GatewayIntentBits.GuildMessages,
      GatewayIntentBits.MessageContent,
    ],
  });

  client.on("ready", () => {
    console.log(`[reclaw] Discord connected as ${client.user.tag}`);
  });

  client.on("messageCreate", async (message) => {
    if (message.author.bot) return;
    const mentioned = message.mentions.users.has(client.user.id);
    const direct = !message.guild;
    if (!mentioned && !direct) return;

    try {
      const reply = await respondToMessage(message.content.replace(`<@${client.user.id}>`, "").trim());
      await message.reply(reply.slice(0, 1900));
    } catch (err) {
      console.error("[reclaw] message failed:", err.message);
      await message.reply("I hit an error while handling that. Run `reclaw doctor`.");
    }
  });

  await client.login(token);
  return client;
}

async function sendDiscord(client, text) {
  const channelId = process.env.DISCORD_CHANNEL_ID;
  if (!client || !channelId) return;
  const channel = await client.channels.fetch(channelId);
  if (channel?.isTextBased()) await channel.send(text);
}

async function main() {
  await ensureMemoryDir();
  await write("agent-state.txt", `started=${new Date().toISOString()}\n`);

  const testMessage = argValue("--test-message");
  if (testMessage) {
    console.log(await respondToMessage(testMessage));
    return;
  }

  const rememberText = argValue("--remember");
  if (rememberText) {
    const result = await remember(rememberText);
    console.log(`Remembered in ${result.file}: ${rememberText}`);
    return;
  }

  const memoryQuery = argValue("--memory-search");
  if (memoryQuery) {
    const matches = await search(memoryQuery);
    if (!matches.length) {
      console.log("No memory matches found.");
      return;
    }
    for (const match of matches) {
      console.log(`- ${match.file}: ${match.preview.replace(/\s+/g, " ").trim()}`);
    }
    return;
  }

  if (args.includes("--heartbeat-once")) {
    await heartbeat();
    return;
  }

  const client = await connectDiscord();
  const send = (text) => sendDiscord(client, text);

  if (process.env.HEARTBEAT_ON_START === "true") {
    await heartbeat({ send });
  }

  const intervalMs = Math.max(1, intervalMinutes) * 60 * 1000;
  setInterval(() => heartbeat({ send }).catch((err) => {
    console.error("[reclaw] heartbeat failed:", err.message);
  }), intervalMs);

  console.log(`[reclaw] ${agentName} running. Heartbeat every ${intervalMinutes} minute(s).`);
}

main().catch((err) => {
  console.error("[reclaw] fatal:", err.message);
  process.exit(1);
});
