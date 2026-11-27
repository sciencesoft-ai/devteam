// Rewrite user-visible text inside JS/TS/TSX string literals, template chunks and
// JSX text, in place. Only the source range of each literal is touched, so code,
// comments and formatting are untouched. Called by scripts/rewrite_strings.py.
//
//   node rewrite_js.js <rules.json>  < file list
// Prints one JSON line: {"files": n, "edits": n}.
"use strict";
const fs = require("fs");
const path = require("path");
const parser = require(path.join(__dirname, "node_modules", "@babel", "parser"));

const rules = JSON.parse(fs.readFileSync(process.argv[2], "utf8")).map((r) => ({
  re: new RegExp(r.find, "g"),
  replace: r.replace,
  proseOnly: !!r.prose_only,
}));

function rewrite(raw, cooked) {
  const prose = /\s/.test(cooked);
  let out = raw;
  for (const r of rules) {
    if (r.proseOnly && !prose) continue;
    out = out.replace(r.re, r.replace);
  }
  return out;
}

function walk(node, cb) {
  if (!node || typeof node.type !== "string") return;
  cb(node);
  for (const key of Object.keys(node)) {
    if (key === "loc" || key === "start" || key === "end" || key === "extra") continue;
    const v = node[key];
    if (Array.isArray(v)) v.forEach((c) => c && typeof c.type === "string" && walk(c, cb));
    else if (v && typeof v.type === "string") walk(v, cb);
  }
}

let files = 0;
let edits = 0;
for (const file of fs.readFileSync(0, "utf8").split(/\r?\n/).filter(Boolean)) {
  const src = fs.readFileSync(file, "utf8");
  if (!/kiro/i.test(src)) continue;
  let ast;
  try {
    ast = parser.parse(src, {
      sourceType: "unambiguous",
      errorRecovery: true,
      plugins: ["jsx", "typescript", "importAttributes", "decorators-legacy", "topLevelAwait"],
    });
  } catch (e) {
    console.error(`rewrite_js: cannot parse ${file}: ${e.message}`);
    process.exit(2);
  }
  const spans = [];
  walk(ast.program, (n) => {
    let cooked = null;
    if (n.type === "StringLiteral") cooked = n.value;
    else if (n.type === "TemplateElement") cooked = n.value.cooked == null ? n.value.raw : n.value.cooked;
    else if (n.type === "JSXText") cooked = n.value;
    if (cooked == null || !/kiro/i.test(cooked)) return;
    const raw = src.slice(n.start, n.end);
    const next = rewrite(raw, cooked);
    if (next !== raw) spans.push([n.start, n.end, next]);
  });
  if (!spans.length) continue;
  spans.sort((a, b) => b[0] - a[0]);
  let out = src;
  for (const [s, e, text] of spans) out = out.slice(0, s) + text + out.slice(e);
  fs.writeFileSync(file, out);
  files += 1;
  edits += spans.length;
}
process.stdout.write(JSON.stringify({ files, edits }) + "\n");
