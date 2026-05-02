import { test } from "node:test";
import assert from "node:assert/strict";
import { envLine } from "../src/config.js";

test("envLine quotes values that need shell-safe escaping", () => {
  assert.equal(envLine("AGENT_NAME", "ReClaw"), "AGENT_NAME=ReClaw");
  assert.equal(envLine("USER_WORK", "Oil & gas ops"), 'USER_WORK="Oil & gas ops"');
  assert.equal(envLine("EMPTY", ""), "EMPTY=");
  assert.equal(envLine("MULTILINE", "one\ntwo"), 'MULTILINE="one two"');
});
