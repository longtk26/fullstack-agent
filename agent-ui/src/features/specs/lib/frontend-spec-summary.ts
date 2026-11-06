export type TPageSummary = { id: string; route: string; title: string; sectionCount: number; operations: string[] };
export type TComponentSummary = { name: string; custom: boolean; pages: string[] };
export type TThemeSummary = {
  style: string | null;
  colorScheme: string | null;
  colors: { name: string; value: string }[];
  headingFont: string | null;
  bodyFont: string | null;
  radius: string | null;
};
export type TFrontendSpecSummary = {
  projectName: string | null;
  mode: string | null;
  pages: TPageSummary[];
  theme: TThemeSummary;
  components: TComponentSummary[];
};

type TLoose = Record<string, unknown>;

function asObject(value: unknown): TLoose {
  return typeof value === "object" && value !== null && !Array.isArray(value) ? (value as TLoose) : {};
}

function asArray(value: unknown): TLoose[] {
  return Array.isArray(value) ? value.filter((item): item is TLoose => typeof item === "object" && item !== null) : [];
}

function asString(value: unknown): string | null {
  return typeof value === "string" ? value : null;
}

/** The page id the API derives when a page has none: `/` → `home`, `/products/[id]` → `products-id`. */
function pageIdFromRoute(route: string): string {
  const parts = route.split("/").filter(Boolean).map((part) => part.replace(/^\[|\]$/g, "").toLowerCase());
  return parts.join("-") || "home";
}

/** Every section of a page, including those nested in layout nodes (`children`). */
function walkSections(sections: TLoose[]): TLoose[] {
  return sections.flatMap((section) => [section, ...walkSections(asArray(section.children))]);
}

/** A tolerant read of a (possibly invalid) FrontendSpec for the review panel (Story 9.7b); never throws. */
export function summarizeFrontendSpec(spec: unknown): TFrontendSpecSummary {
  const root = asObject(spec);
  const project = asObject(root.project);
  const theme = asObject(root.theme);
  const typography = asObject(theme.typography);
  const custom = new Set(asArray(root.components).map((component) => asString(component.name)).filter(Boolean));
  const forms = new Map(asArray(root.forms).map((form) => [asString(form.id), asString(form.operationId)]));
  const usedBy = new Map<string, Set<string>>();

  const pages = asArray(root.pages).map((page) => {
    const route = asString(page.route) ?? "?";
    const id = asString(page.id) ?? pageIdFromRoute(route);
    const sections = walkSections(asArray(page.sections));
    const operations = new Set<string>();
    for (const section of sections) {
      const component = asString(section.component);
      if (component) usedBy.set(component, (usedBy.get(component) ?? new Set()).add(id));
      const operationId = asString(asObject(section.data).operationId);
      if (operationId) operations.add(operationId);
      const formOperation = forms.get(asString(section.form) ?? asString(asObject(section.content).form));
      if (formOperation) operations.add(formOperation);
    }
    return {
      id,
      route,
      title: asString(page.title) ?? id,
      sectionCount: sections.length,
      operations: [...operations],
    };
  });

  for (const name of custom) if (name && !usedBy.has(name)) usedBy.set(name, new Set());
  const components = [...usedBy.entries()]
    .map(([name, used]) => ({ name, custom: custom.has(name), pages: [...used] }))
    .sort((a, b) => Number(b.custom) - Number(a.custom) || a.name.localeCompare(b.name));

  return {
    projectName: asString(project.name),
    mode: asString(project.mode),
    pages,
    theme: {
      style: asString(theme.style),
      colorScheme: asString(theme.colorScheme),
      colors: Object.entries(asObject(theme.colors)).flatMap(([name, value]) =>
        typeof value === "string" ? [{ name, value }] : [],
      ),
      headingFont: asString(typography.headingFont),
      bodyFont: asString(typography.bodyFont),
      radius: asString(theme.radius),
    },
    components,
  };
}

// Epic 22: the app outline of a dynamic app draft (`project.flow: "app"`), for the draft review.
export type TAppEntitySummary = {
  name: string;
  label: string;
  plural: string;
  listFields: string[];
  listStyle: string | null;
  /** Epic 23: the brief's view of the entity's list. */
  view: string | null;
  inNav: boolean;
};
export type TAppOutlineSummary = {
  name: string | null;
  tagline: string | null;
  home: string;
  nav: { entity: string; label: string }[];
  entities: TAppEntitySummary[];
  dashboard: { label: string; kind: string; entity: string | null }[];
  landing: boolean;
  /** Epic 23: the brief in one line, and its looks. */
  design: string | null;
  looks: string[];
};

function asStrings(value: unknown): string[] {
  return Array.isArray(value) ? value.filter((item): item is string => typeof item === "string") : [];
}

/** The app outline of an app draft, or null for sites and legacy dynamic drafts; tolerant, never throws. */
export function summarizeAppOutline(spec: unknown): TAppOutlineSummary | null {
  const root = asObject(spec);
  if (asObject(root.project).flow !== "app" || !("app" in root)) return null;
  const app = asObject(root.app);
  const entities = asObject(app.entities);
  const labelOf = (name: string) => {
    const entity = asObject(entities[name]);
    return asString(entity.plural) ?? asString(entity.label) ?? name;
  };
  const nav = asArray(app.nav).flatMap((item) => {
    const entity = asString(item.entity);
    return entity ? [{ entity, label: asString(item.label) ?? labelOf(entity) }] : [];
  });
  const navEntities = new Set(nav.map((item) => item.entity));
  return {
    name: asString(app.name),
    tagline: asString(app.tagline),
    home: asString(app.home) ?? "dashboard",
    nav,
    entities: Object.entries(entities).map(([name, value]) => {
      const entity = asObject(value);
      const label = asString(entity.label) ?? name;
      return {
        name,
        label,
        plural: asString(entity.plural) ?? label,
        listFields: asStrings(entity.listFields).map((field) => asString(asObject(entity.fieldLabels)[field]) ?? field),
        listStyle: asString(entity.listStyle),
        view: asString(asObject(asObject(asObject(app.design).entities)[name]).view),
        inNav: navEntities.has(name),
      };
    }),
    dashboard: asArray(app.dashboard).map((item) => ({
      label: asString(item.label) ?? "?",
      kind: asString(item.kind) ?? "figure",
      entity: asString(item.entity),
    })),
    landing: Object.keys(asObject(app.landing)).length > 0,
    design: designLine(asObject(app.design)),
    looks: asArray(asObject(app.design).looks).flatMap((look) => {
      const recipe = asString(look.recipe);
      return recipe ? [recipe] : [];
    }),
  };
}

function designLine(design: Record<string, unknown>): string | null {
  const parts = [
    asString(design.archetype),
    asString(design.shell) && `${asString(design.shell)} shell`,
    asString(design.homeView) && `opens on ${asString(design.homeView)}`,
  ].filter(Boolean);
  return parts.length ? parts.join(" · ") : null;
}
