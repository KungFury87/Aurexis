const fs = require("fs");
const src = fs.readFileSync("test_decode_engine.js", "utf8");
const lines = src.split("\n");

const stageStart = parseInt(process.argv[2]);
const stageEnd = parseInt(process.argv[3] || process.argv[2]);

// Setup: lines 0-57 (imports, test harness, helpers)
const setup = lines.slice(0, 58).join("\n");

// Extra requires that come later in the file
const extraReqs = `
const renderer = require("./renderer");
const decodeEngine = require("./index");
`;

// Find target stage range
let targetStart = -1, targetEnd = lines.length - 1;
for (let i = 0; i < lines.length; i++) {
  const m = lines[i].match(/STAGE\s+(\d+)/);
  if (m) {
    const n = parseInt(m[1]);
    if (n === stageStart && targetStart === -1) targetStart = i - 1;
    if (n === stageEnd + 1 && targetStart !== -1) { targetEnd = i - 3; break; }
  }
}

// Stop before Summary section
for (let i = Math.max(targetStart, 0); i <= targetEnd; i++) {
  if (lines[i].match(/^\/\/\s*={5,}/) && i > targetStart + 3) {
    const next = lines[i+1] || "";
    if (next.match(/^\/\/\s*Summary\s*$/i)) { targetEnd = i - 2; break; }
  }
}

let body = lines.slice(targetStart, targetEnd + 1).join("\n");
// Strip duplicate requires that _run_stages already injects
body = body.replace(/^const renderer = require\(.*\);?\s*$/gm, "// (renderer already required)");
body = body.replace(/^const decodeEngine = require\(.*\);?\s*$/gm, "// (decodeEngine already required)");
const code = setup + "\n" + extraReqs + "\n" + body + "\n\nconsole.log('---STAGES DONE---');\nconsole.log('passed:', passed, 'failed:', failed);";
fs.writeFileSync("_stage_test.js", code);
console.log(`Setup: 0-57, Extra reqs added, Target: ${targetStart}-${targetEnd}`);
