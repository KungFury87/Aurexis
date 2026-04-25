"use strict";
const renderer = require("./renderer");
const decodeEngine = require("./index");
const codec = require("./codec");
let passed = 0, failed = 0, total = 0;
function test(name, fn) {
  total++;
  try { fn(); passed++; console.log(`  ✓ ${name}`); }
  catch (e) { failed++; console.log(`  FAIL: ${name}\n        ${e.message}`); }
}
function assert(cond, msg) { if (!cond) throw new Error(msg || "assertion failed"); }
assert.strictEqual = function(a, b, msg) {
  if (a !== b) throw new Error((msg || "") + ` expected ${JSON.stringify(b)}, got ${JSON.stringify(a)}`);
};
const fs = require("fs");
const lines = fs.readFileSync("test_decode_engine.js", "utf8").split("\n");
const startStage = process.argv[2] || "126";
const endStage = process.argv[3] || "131";
let startLine = 0, endLine = lines.length;
for (let i = 0; i < lines.length; i++) {
  if (lines[i].includes("STAGE " + startStage + ":")) { startLine = i - 1; break; }
}
for (let i = startLine + 5; i < lines.length; i++) {
  const nextStage = parseInt(endStage) + 1;
  if (lines[i].includes("STAGE " + nextStage + ":") || (lines[i].includes("// Summary") && i > startLine + 5)) {
    endLine = i; break;
  }
}
console.log("Running stages " + startStage + "-" + endStage + " (lines " + (startLine+1) + "-" + endLine + ")");
eval(lines.slice(startLine, endLine).join("\n"));
console.log("\n" + passed + "/" + total + " passed, " + failed + " failed");
if (failed > 0) process.exit(1);
