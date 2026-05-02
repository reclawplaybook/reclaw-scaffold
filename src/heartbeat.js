import { append, ensureMemoryDir, search, todayFile } from "./memory.js";

export function tierIntervalMinutes(tier = process.env.CLAUDE_TIER || "pro") {
  if (tier === "max20x") return 15;
  if (tier === "max5x") return 30;
  return 60;
}

export async function heartbeat({ send = null } = {}) {
  await ensureMemoryDir();
  const pending = await search("TODO");
  const urgent = pending.filter((item) => /urgent|today|blocked/i.test(item.preview));
  const stamp = new Date().toISOString();

  if (!urgent.length) {
    await append(todayFile(), `\n- ${stamp} HEARTBEAT_OK\n`);
    console.log("HEARTBEAT_OK");
    return { ok: true, status: "HEARTBEAT_OK" };
  }

  const message = `Heartbeat found ${urgent.length} memory item(s) that may need attention.`;
  await append(todayFile(), `\n- ${stamp} ${message}\n`);
  if (send) await send(message);
  return { ok: true, status: "attention", message, items: urgent };
}
