/**
 * Epic 23: an app draft's design brief, read from and written into the FrontendSpec text (`app.design`). Every edit is
 * presentation only (the look, the shell, an entity's view): the kit reads it; bindings and screens do not change.
 */

export const RECIPES = [
  "minimal",
  "swiss",
  "material",
  "enterprise",
  "soft",
  "clay",
  "glass",
  "aurora",
  "brutalist",
  "neon",
  "playful",
  "editorial",
] as const;
export const SHELLS = ["sidebar", "rail", "topbar", "topbar-tabs"] as const;
export const VIEWS = ["table", "cards", "media-grid", "feed", "board", "calendar"] as const;

export type TLook = { recipe: string; reason?: string };
export type TAppDesign = {
  archetype: string | null;
  shell: string | null;
  homeView: string | null;
  mainEntity: string | null;
  looks: TLook[];
  recipe: string | null;
  views: { entity: string; view: string }[];
  areas: { id: string; label: string; roles: string[] }[];
  replaced: string[];
};

function parse(text: string): Record<string, unknown> | null {
  try {
    const value = JSON.parse(text) as unknown;
    return value && typeof value === "object" && !Array.isArray(value) ? (value as Record<string, unknown>) : null;
  } catch {
    return null;
  }
}

function obj(value: unknown): Record<string, unknown> {
  return value && typeof value === "object" && !Array.isArray(value) ? (value as Record<string, unknown>) : {};
}

function str(value: unknown): string | null {
  return typeof value === "string" ? value : null;
}

/** The brief of an app FrontendSpec, or null for a site, an older app or text that is not JSON. */
export function readAppDesign(text: string): TAppDesign | null {
  const spec = parse(text);
  if (!spec || obj(spec.project).flow !== "app") return null;
  const app = obj(spec.app);
  if (!("design" in app)) return null;
  const design = obj(app.design);
  const looks = (Array.isArray(design.looks) ? design.looks : []).flatMap((look) => {
    const recipe = str(obj(look).recipe);
    return recipe ? [{ recipe, reason: str(obj(look).reason) ?? undefined }] : [];
  });
  return {
    archetype: str(design.archetype),
    shell: str(design.shell),
    homeView: str(design.homeView),
    mainEntity: str(design.mainEntity),
    looks,
    recipe: str(design.recipe) ?? looks[0]?.recipe ?? null,
    views: Object.entries(obj(design.entities)).map(([entity, value]) => ({ entity, view: str(obj(value).view) ?? "table" })),
    areas: (Array.isArray(app.areas) ? app.areas : []).map((area) => ({
      id: str(obj(area).id) ?? "",
      label: str(obj(area).label) ?? "",
      roles: (Array.isArray(obj(area).roles) ? (obj(area).roles as unknown[]) : []).filter((r): r is string => typeof r === "string"),
    })),
    replaced: (Array.isArray(design.replaced) ? design.replaced : []).filter((line): line is string => typeof line === "string"),
  };
}

type TEdit = { recipe: string } | { shell: string } | { entity: string; view: string };

/** The text with one design value changed (2-space JSON, as the editor writes), or null when it cannot be applied. */
export function editAppDesign(text: string, edit: TEdit): string | null {
  const spec = parse(text);
  if (!spec || obj(spec.project).flow !== "app") return null;
  const app = obj(spec.app);
  const design = { ...obj(app.design) };
  if ("recipe" in edit) {
    if (!(RECIPES as readonly string[]).includes(edit.recipe)) return null;
    design.recipe = edit.recipe;
  } else if ("shell" in edit) {
    if (!(SHELLS as readonly string[]).includes(edit.shell)) return null;
    design.shell = edit.shell;
  } else {
    if (!(VIEWS as readonly string[]).includes(edit.view)) return null;
    const entities = { ...obj(design.entities) };
    entities[edit.entity] = { ...obj(entities[edit.entity]), view: edit.view };
    design.entities = entities;
  }
  return JSON.stringify({ ...spec, app: { ...app, design } }, null, 2);
}

/** A short line of the brief for the draft summary. */
export function describeAppDesign(design: TAppDesign): string {
  const parts = [design.archetype, design.shell && `${design.shell} shell`, design.homeView && `opens on ${design.homeView}`];
  return parts.filter(Boolean).join(" · ");
}
