#!/usr/bin/env node
import { writeEnvFile } from "../src/config.js";

const target = process.argv[2] || ".env";
const values = {};

for (const pair of process.argv.slice(3)) {
  const index = pair.indexOf("=");
  if (index <= 0) continue;
  values[pair.slice(0, index)] = pair.slice(index + 1);
}

await writeEnvFile(target, values);
