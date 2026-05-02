import { test } from "node:test";
import assert from "node:assert/strict";
import { mkdtemp } from "fs/promises";
import { tmpdir } from "os";
import { join } from "path";

test("memory module writes, reads, appends, and searches", async () => {
  const root = await mkdtemp(join(tmpdir(), "reclaw-memory-"));
  process.env.RECLAW_HOME = root;
  process.env.MEMORY_DIR = "memory";
  const memory = await import(`../src/memory.js?root=${Date.now()}`);

  await memory.write("notes.md", "first line");
  await memory.append("notes.md", "\nurgent TODO");
  assert.equal(await memory.read("notes.md"), "first line\nurgent TODO");

  const matches = await memory.search("urgent");
  assert.equal(matches.length, 1);
  assert.equal(matches[0].file, "notes.md");

  const result = await memory.remember("ship the playbook");
  assert.equal(result.file, memory.todayFile());
  assert.match(await memory.read(memory.todayFile()), /ship the playbook/);
});
