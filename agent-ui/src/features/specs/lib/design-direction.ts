import type { TDesignDirection } from "../types";

type TSection = { component?: unknown; content?: Record<string, unknown> };
type TSpec = Record<string, unknown> & {
  theme?: { colorScheme?: string; typography?: { scale?: string }; direction?: { productType?: string } };
  pages?: { route?: string; sections?: TSection[] }[];
};

const HOME_ROUTE = "/";

/**
 * Sections in the direction's order; any other section stays right after the one it followed. Same rule as
 * `reorder_sections` in the agent (orchestrator/design_direction.py).
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
 * The FrontendSpec with a direction's theme, home page order and hero layout; pages, content and edits elsewhere are
 * kept. The spec's light / dark choice and type scale stay unless the palette is dark (as in `apply_direction`).
 */
export function applyDirection(spec: TSpec, direction: TDesignDirection): TSpec {
  const current = spec.theme ?? {};
  const theme = structuredClone(direction.theme);
  if (theme.colorScheme !== "dark") theme.colorScheme = (current.colorScheme as typeof theme.colorScheme) ?? "light";
  theme.typography.scale = current.typography?.scale ?? "default";
  const pages = (spec.pages ?? []).map((page) => {
    if (page.route !== HOME_ROUTE) return page;
    let heroDone = false;
    const sections = reorderSections(page.sections ?? [], direction.homeOrder).map((section) => {
      if (heroDone || section.component !== "Hero") return section;
      heroDone = true;
      return { ...section, content: { ...section.content, variant: direction.heroVariant } };
    });
    return { ...page, sections };
  });
  return { ...spec, theme, pages };
}

/** The editor text with the direction applied, or null while the JSON does not parse. */
export function applyDirectionToText(text: string, direction: TDesignDirection): string | null {
  try {
    const spec = JSON.parse(text) as unknown;
    if (!spec || typeof spec !== "object" || Array.isArray(spec)) return null;
    return `${JSON.stringify(applyDirection(spec as TSpec, direction), null, 2)}\n`;
  } catch {
    return null;
  }
}

/** Whether the spec's theme is this direction's (same product type, palette and fonts). */
export function isCurrentDirection(text: string, direction: TDesignDirection): boolean {
  try {
    const theme = (JSON.parse(text) as TSpec).theme as TDesignDirection["theme"] | undefined;
    return (
      theme?.direction?.productType === direction.productType &&
      theme.colors?.primary === direction.theme.colors.primary &&
      theme.typography?.headingFont === direction.theme.typography.headingFont &&
      theme.typography?.bodyFont === direction.theme.typography.bodyFont &&
      theme.style === direction.theme.style
    );
  } catch {
    return false;
  }
}
