import type { TDesignDirection, TPoolSection } from "../types";

type TSection = { id?: unknown; component?: unknown; content?: Record<string, unknown>; children?: TSection[] };
type TPage = { route?: string; rhythm?: string; sections?: TSection[] };
type TSpec = Record<string, unknown> & {
  theme?: { colorScheme?: string; typography?: { scale?: string }; direction?: Record<string, unknown> };
  pages?: TPage[];
};

const HOME_ROUTE = "/";
/** Sections whose form a direction card sets (Story 20.4); as `FORM_SECTIONS` in the agent. */
const FORM_SECTIONS = ["Features", "Testimonials", "Stats"];

export const PHOTO_STYLES_BY_PRESET: Record<string, string> = {
  minimal: "warm natural light, soft shadows, muted tones",
  editorial: "rich contrast, thoughtful composition, warm film tones",
  playful: "bright saturated colours, high contrast, crisp cheerful light",
  corporate: "clean professional lighting, balanced exposure, modern setting",
  dashboard: "crisp focused lighting, clear subject, neutral background",
};

/**
 * Sections in the direction's order; any other section stays right after the one it followed. Same rule as
 * `reorder_sections` in the agent (orchestrator/design_direction.py). Used by directions without `home`.
 */
export function reorderSections<T extends TSection>(sections: T[], order: string[]): T[] {
  const rank = new Map(order.map((name, position) => [name, position]));
  let last = -1;
  const keyed = sections.map((section, position) => {
    const known = typeof section.component === "string" ? rank.get(section.component) : undefined;
    if (known !== undefined) last = known;
    return { key: [known ?? last, known === undefined ? 1 : 0, position], section };
  });
  keyed.sort((a, b) => a.key[0] - b.key[0] || a.key[1] - b.key[1] || a.key[2] - b.key[2]);
  return keyed.map((item) => item.section);
}

/**
 * The home page a direction composes, by section id, from the drafted pool (Story 20.9). A section's current
 * version wins over the pool's, so edits are kept; sections the pool never had (added by the user) stay after the
 * section they followed. Same rule as `compose_home` in the agent.
 */
export function composeHome(sections: TSection[], home: string[], pool: TSection[]): TSection[] {
  const ids = (list: TSection[]) => list.filter((s): s is TSection & { id: string } => typeof s?.id === "string");
  const known = new Set(ids(pool).map((s) => s.id));
  const byId = new Map<string, TSection>(ids(pool).map((s) => [s.id, s]));
  for (const section of ids(sections)) if (known.has(section.id)) byId.set(section.id, section);
  const extras = new Map<string | null, TSection[]>();
  let last: string | null = null;
  for (const section of sections) {
    if (typeof section?.id === "string" && known.has(section.id)) last = section.id;
    else extras.set(last, [...(extras.get(last) ?? []), section]);
  }
  const out = [...(extras.get(null) ?? [])];
  extras.delete(null);
  for (const id of home) {
    const section = byId.get(id);
    if (!section) continue;
    out.push(structuredClone(section));
    out.push(...(extras.get(id) ?? []));
    extras.delete(id);
  }
  for (const rest of extras.values()) out.push(...rest);
  return out;
}

function hasItemImages(section: TSection): boolean {
  const items = section.content?.items;
  return Array.isArray(items) && items.some((item) => item && typeof item === "object" && "image" in item && item.image);
}

/** The direction's section forms on every section of a page (nested ones too); as `apply_forms` in the agent. */
function withForms(sections: TSection[], forms: Record<string, string>): TSection[] {
  return sections.map((section) => {
    const children = section.children ? withForms(section.children, forms) : undefined;
    let next: TSection = children ? { ...section, children } : section;
    const name = typeof section.component === "string" ? section.component : "";
    if (FORM_SECTIONS.includes(name)) {
      let form = forms[name];
      if (form === "alternating" && !hasItemImages(section)) form = "list";
      if (form || (section.content && "form" in section.content)) {
        const content = { ...(section.content ?? {}) };
        if (form) content.form = form;
        else delete content.form;
        next = { ...next, content };
      }
    }
    return next;
  });
}

/**
 * The FrontendSpec with a direction's theme, home page and hero layout; pages, content and edits elsewhere are
 * kept. The spec's light / dark choice and type scale stay unless the palette is dark (as in `apply_direction`).
 * A direction card (Story 20.4) also sets the section forms and the page rhythm; with `home` (Story 20.9) the home
 * page is composed from `pool`, the drafted home sections.
 */
export function applyDirection(spec: TSpec, direction: TDesignDirection, pool?: TPoolSection[]): TSpec {
  const current = spec.theme ?? {};
  const theme = structuredClone(direction.theme);
  if (theme.colorScheme !== "dark") theme.colorScheme = (current.colorScheme as typeof theme.colorScheme) ?? "light";
  theme.typography.scale = current.typography?.scale ?? "default";
  const photoStyle =
    direction.photoStyle ?? PHOTO_STYLES_BY_PRESET[direction.theme.style] ?? PHOTO_STYLES_BY_PRESET.minimal;
  const assets = Array.isArray(spec.assets)
    ? (spec.assets as Record<string, unknown>[]).map((asset) => {
        if (!asset || typeof asset !== "object") return asset;
        const source = typeof asset.source === "string" ? asset.source : "";
        const isPhoto = source === "photo" || (source.startsWith("upload:") && Boolean(asset.prompt));
        if (isPhoto && !asset.style && photoStyle) {
          return { ...asset, style: photoStyle };
        }
        return asset;
      })
    : spec.assets;
  const pages = (spec.pages ?? []).map((page) => {
    let next: TPage = page;
    if (page.route === HOME_ROUTE) {
      const current = page.sections ?? [];
      let sections = direction.home?.length
        ? composeHome(current, direction.home, (pool as TSection[] | undefined) ?? current)
        : reorderSections(current, direction.homeOrder);
      let heroDone = false;
      sections = sections.map((section) => {
        if (heroDone || section.component !== "Hero") return section;
        heroDone = true;
        return { ...section, content: { ...section.content, variant: direction.heroVariant } };
      });
      next = { ...next, sections };
    }
    if (direction.sectionForms !== undefined) {
      next = { ...next, sections: withForms(next.sections ?? [], direction.sectionForms ?? {}) };
    }
    if (direction.rhythm !== undefined) {
      next = { ...next };
      if (direction.rhythm && direction.rhythm !== "uniform") next.rhythm = direction.rhythm;
      else delete next.rhythm;
    }
    return next;
  });
  return { ...spec, theme, pages, ...(assets !== undefined ? { assets } : {}) };
}

/** The editor text with the direction applied, or null while the JSON does not parse. */
export function applyDirectionToText(text: string, direction: TDesignDirection, pool?: TPoolSection[]): string | null {
  try {
    const spec = JSON.parse(text) as unknown;
    if (!spec || typeof spec !== "object" || Array.isArray(spec)) return null;
    return `${JSON.stringify(applyDirection(spec as TSpec, direction, pool), null, 2)}\n`;
  } catch {
    return null;
  }
}

/** Whether the spec's theme is this direction's (same card or product type, palette and fonts). */
export function isCurrentDirection(text: string, direction: TDesignDirection): boolean {
  try {
    const theme = (JSON.parse(text) as TSpec).theme as TDesignDirection["theme"] | undefined;
    const recorded = theme?.direction ?? {};
    const same = direction.source === "card" ? recorded.name === direction.name : recorded.productType === direction.productType;
    return (
      same &&
      theme?.colors?.primary === direction.theme.colors.primary &&
      theme.typography?.headingFont === direction.theme.typography.headingFont &&
      theme.typography?.bodyFont === direction.theme.typography.bodyFont &&
      theme.style === direction.theme.style
    );
  } catch {
    return false;
  }
}
