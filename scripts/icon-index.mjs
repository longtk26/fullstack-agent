// Icon index for the FrontendSpec's icon resolver (Story 20.5): every icon of the pinned base's two sets with the
// words it can be found by (its name, tags and categories), written to <base>/icon-index.json. Lucide icons are keyed
// by their file name (`truck`, imported from `lucide-react/icons/truck`), Phosphor icons by their component name
// (`Truck`, from `@phosphor-icons/react/dist/ssr/Truck`). Not copied into
// projects. Runs inside node:22 (network): it packs the metadata packages at the versions the base pins.
//
//   node scripts/icon-index.mjs agent-api/templates/nextjs_base      # called by scripts/frontend-base.sh
import { execFileSync } from "node:child_process";
import { mkdtempSync, readFileSync, readdirSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";

// @phosphor-icons/core carries the tags and categories of @phosphor-icons/react (same icon set, its own versions).
const PHOSPHOR_CORE_VERSION = "2.1.1";

const base = process.argv[2] ?? ".";
const lock = readFileSync(join(base, "pnpm-lock.yaml"), "utf8");
const pinned = (name) => {
  // Scoped names are quoted in the lock: `  '@scope/name@1.2.3':`.
  const escaped = name.replace(/[/@]/g, "\\$&");
  const match = lock.match(new RegExp(`\\n  '?${escaped}@(\\d+\\.\\d+\\.\\d+)'?:`));
  if (!match) throw new Error(`${name} is not in the base's lock`);
  return match[1];
};
const lucide = pinned("lucide-react");
const phosphor = pinned("@phosphor-icons/react");

const work = mkdtempSync(join(tmpdir(), "icon-index-"));
const unpack = (spec) => {
  const file = execFileSync("npm", ["pack", spec, "--silent"], { cwd: work, encoding: "utf8" }).trim();
  const dir = join(work, file.replace(/\.tgz$/, ""));
  execFileSync("mkdir", ["-p", dir]);
  execFileSync("tar", ["xzf", join(work, file), "-C", dir]);
  return join(dir, "package");
};

const words = (...lists) => [...new Set(lists.flat().map((word) => String(word).toLowerCase()))].sort();

const lucideTags = JSON.parse(readFileSync(join(unpack(`lucide-static@${lucide}`), "tags.json"), "utf8"));
// Lucide by file name (`lucide-react/icons/<name>`); its component name is the name in PascalCase.
const lucideIcons = Object.fromEntries(
  Object.entries(lucideTags).map(([name, tags]) => [name, words(name.split("-"), tags)]),
);

// Renamed Lucide icons stay importable under their old names (`alert-triangle` → `triangle-alert`): lucide-react ships
// each old name as a file that re-exports the current one. Engines often write the old names, so the index keeps them.
const lucideReact = join(unpack(`lucide-react@${lucide}`), "dist", "esm", "icons");
const lucideAliases = Object.fromEntries(
  readdirSync(lucideReact)
    .filter((file) => file.endsWith(".mjs"))
    .flatMap((file) => {
      const target = readFileSync(join(lucideReact, file), "utf8").match(/export \{ default \} from '\.\/([a-z0-9-]+)\.mjs'/);
      return target && target[1] in lucideIcons ? [[file.replace(/\.mjs$/, ""), target[1]]] : [];
    }),
);

const react = unpack(`@phosphor-icons/react@${phosphor}`);
const shipped = new Set(
  readdirSync(join(react, "dist", "ssr"))
    .filter((file) => file.endsWith(".es.js") && file !== "index.es.js")
    .map((file) => file.replace(/\.es\.js$/, "")),
);
const core = await import(join(unpack(`@phosphor-icons/core@${PHOSPHOR_CORE_VERSION}`), "dist", "index.mjs"));
const phosphorIcons = Object.fromEntries(
  core.icons
    .filter((icon) => shipped.has(icon.pascal_name))
    .map((icon) => [icon.pascal_name, words(icon.name.split("-"), icon.tags, icon.categories)]),
);

const sorted = (icons) => Object.fromEntries(Object.entries(icons).sort(([a], [b]) => a.localeCompare(b)));
const index = {
  about: "Icon names with their words (name, tags, categories) for the FrontendSpec icon resolver (Story 20.5).",
  lucide: {
    package: "lucide-react",
    version: lucide,
    tags: `lucide-static@${lucide}`,
    icons: sorted(lucideIcons),
    aliases: sorted(lucideAliases),
  },
  phosphor: {
    package: "@phosphor-icons/react",
    version: phosphor,
    tags: `@phosphor-icons/core@${PHOSPHOR_CORE_VERSION}`,
    icons: sorted(phosphorIcons),
  },
};
writeFileSync(join(base, "icon-index.json"), `${JSON.stringify(index)}\n`);
console.log(
  `icon-index.json: ${Object.keys(lucideIcons).length} lucide (${Object.keys(lucideAliases).length} old names), ` +
    `${Object.keys(phosphorIcons).length} phosphor`,
);
