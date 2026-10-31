export type TPageSummary = { id: string; route: string; title: string; sectionCount: number; operations: string[] };
export type TComponentSummary = { name: string; custom: boolean; pages: string[] };
export type TJourneyStepSummary = {
  do: string;
  page?: string | null;
  section?: string | null;
  action?: string | null;
  operationId?: string | null;
  record?: string | number | null;
  values?: Record<string, unknown> | null;
  text?: string | null;
  count?: number | null;
  changed?: { field: string; record?: string | number | null } | null;
  live?: boolean;
};
export type TJourneySummary = {
  id: string;
  title: string;
  goal: string | null;
  steps: TJourneyStepSummary[];
};
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
  journeys: TJourneySummary[];
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

  const journeys: TJourneySummary[] = asArray(root.journeys).map((j) => {
    const id = asString(j.id) ?? "";
    const title = asString(j.title) ?? id;
    const goal = asString(j.goal);
    const steps: TJourneyStepSummary[] = asArray(j.steps).map((s) => {
      const changedObj = asObject(s.changed);
      return {
        do: asString(s.do) ?? "visit",
        page: asString(s.page),
        section: asString(s.section),
        action: asString(s.action),
        operationId: asString(s.operationId),
        record: typeof s.record === "number" || typeof s.record === "string" ? s.record : null,
        values: asObject(s.values),
        text: asString(s.text),
        count: typeof s.count === "number" ? s.count : null,
        changed: changedObj.field
          ? {
              field: String(changedObj.field),
              record:
                typeof changedObj.record === "number" || typeof changedObj.record === "string"
                  ? changedObj.record
                  : null,
            }
          : null,
        live: Boolean(s.live),
      };
    });
    return { id, title, goal, steps };
  });

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
    journeys,
  };
}
