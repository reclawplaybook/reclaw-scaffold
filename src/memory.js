import { appendFile, mkdir, readFile, readdir, rename, writeFile } from "fs/promises";
import { join, resolve } from "path";

const root = resolve(process.env.RECLAW_HOME || process.cwd());
const memoryDir = resolve(root, process.env.MEMORY_DIR || "memory");

function safeName(filename) {
  if (!filename || filename.includes("..") || filename.startsWith("/") || filename.includes("\\")) {
    throw new Error("Unsafe memory filename");
  }
  return filename;
}

export async function ensureMemoryDir() {
  await mkdir(memoryDir, { recursive: true });
  return memoryDir;
}

export async function read(filename) {
  await ensureMemoryDir();
  return readFile(join(memoryDir, safeName(filename)), "utf8");
}

export async function write(filename, content) {
  await ensureMemoryDir();
  const target = join(memoryDir, safeName(filename));
  const temp = `${target}.${process.pid}.tmp`;
  await writeFile(temp, String(content), "utf8");
  await rename(temp, target);
}

export async function append(filename, content) {
  await ensureMemoryDir();
  await appendFile(join(memoryDir, safeName(filename)), String(content), "utf8");
}

export async function remember(content, { date = new Date(), tag = "memory" } = {}) {
  const text = String(content || "").trim();
  if (!text) throw new Error("Nothing to remember");
  const stamp = date.toISOString();
  const line = `\n- ${stamp} [${tag}] ${text}\n`;
  await append(todayFile(date), line);
  return { file: todayFile(date), line: line.trim() };
}

export async function search(query) {
  await ensureMemoryDir();
  const needle = String(query || "").toLowerCase();
  if (!needle) return [];
  const files = await readdir(memoryDir);
  const matches = [];
  for (const file of files.filter((name) => name.endsWith(".md") || name.endsWith(".txt"))) {
    const body = await readFile(join(memoryDir, file), "utf8");
    if (body.toLowerCase().includes(needle)) {
      matches.push({ file, preview: body.slice(0, 240) });
    }
  }
  return matches;
}

export function todayFile(date = new Date()) {
  return `${date.toISOString().slice(0, 10)}.md`;
}
