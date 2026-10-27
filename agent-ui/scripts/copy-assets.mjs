// Copies static assets the UI serves from public/: Monaco's AMD build (self-hosted, so the JSON editor works
// offline) and the repo's examples/ (BackendSpecs, Frontend-Agent site JSON, FrontendSpecs) plus an index of them.
import { cpSync, existsSync, mkdirSync, readFileSync, readdirSync, rmSync, writeFileSync } from "node:fs";
import { join } from "node:path";

const root = process.cwd();

function copyMonaco() {
  const pkgDir = join(root, "node_modules", "monaco-editor");
  const { version } = JSON.parse(readFileSync(join(pkgDir, "package.json"), "utf8"));
  const target = join(root, "public", "monaco");
  const stamp = join(target, "VERSION");
  if (existsSync(stamp) && readFileSync(stamp, "utf8") === version) return;
  rmSync(target, { recursive: true, force: true });
  cpSync(join(pkgDir, "min", "vs"), join(target, "vs"), { recursive: true });
  writeFileSync(stamp, version);
  console.log(`monaco-editor ${version} copied to public/monaco`);
}

function copyExamples() {
  const source = process.env.EXAMPLES_DIR ?? join(root, "..", "examples");
  const target = join(root, "public", "examples");
  if (!existsSync(source)) {
    console.warn(`examples not found at ${source}; "Load example" will be empty`);
    return;
  }
  rmSync(target, { recursive: true, force: true });
  mkdirSync(target, { recursive: true });
  const index = {};
  for (const kind of ["specs", "frontend", "frontend-specs"]) {
    const dir = join(source, kind);
    if (!existsSync(dir)) continue;
    cpSync(dir, join(target, kind), { recursive: true });
    index[kind] = readdirSync(dir)
      .filter((name) => name.endsWith(".json"))
      .sort()
      .map((name) => ({ name: name.replace(/\.json$/, ""), path: `/examples/${kind}/${name}` }));
  }
  writeFileSync(join(target, "index.json"), JSON.stringify(index, null, 2));
}

copyMonaco();
copyExamples();
