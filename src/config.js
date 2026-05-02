import { writeFile } from "fs/promises";

export function envLine(key, value) {
  const normalized = String(value ?? "").replace(/\r?\n/g, " ").trim();
  if (!normalized) return `${key}=`;
  if (/^[A-Za-z0-9_./:@+-]+$/.test(normalized)) return `${key}=${normalized}`;
  return `${key}=${JSON.stringify(normalized)}`;
}

export async function writeEnvFile(path, values) {
  const lines = [
    "# ReClaw agent configuration",
    ...Object.entries(values).map(([key, value]) => envLine(key, value)),
    "",
  ];
  await writeFile(path, lines.join("\n"), "utf8");
}
