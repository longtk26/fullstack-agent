import data from "@/content/app.json";

/** One action of a section (Story 22.3): a link to a page, or a mutation (with a confirm, or a form in a dialog). */
export type TAppAction = {
  id: string;
  label: string;
  kind: "link" | "mutation";
  page?: string;
  params?: Record<string, unknown>;
  operationId?: string;
  form?: string;
  confirm?: string | boolean;
  variant?: "default" | "outline" | "secondary" | "ghost" | "destructive";
  onSuccess?: { toast?: string; navigate?: string };
};

export type TAppLink = { page: string; label: string; params?: Record<string, unknown> };

export type TListControls = { search?: boolean; filters?: string[]; sort?: string[] };

/** A section's content as the screen planner writes it; each component reads its part. */
export type TAppContent = {
  entity?: string;
  title?: string;
  label?: string;
  style?: "table" | "cards";
  controls?: TListControls;
  actions?: TAppAction[];
  create?: TAppLink;
  tab?: string;
  variant?: "recent" | "summary";
  kind?: "figure" | "bar" | "line" | "area" | "pie";
  groupBy?: string;
  fn?: string;
  field?: string;
};

/** One app section as the screen planner wrote it (Epic 22): its binding is in `data`, `form` and `content`. */
export type TAppSection = {
  id: string;
  component: string;
  content?: TAppContent;
  data?: {
    kind: "operation";
    operationId: string;
    action: string | null;
    params: Record<string, unknown>;
    fields: string[];
  };
  form?: string;
};

export type TAppPage = { title: string; route: string; sections: TAppSection[] };

export type TAppNavItem = { label: string; href: string; icon: string };

export type TFieldType =
  | "string"
  | "text"
  | "integer"
  | "number"
  | "boolean"
  | "date"
  | "datetime"
  | "enum"
  | "reference"
  | "summary"
  | "list"
  | "object";

export type TAppEntity = {
  label: string;
  plural: string;
  displayField?: string;
  listFields: string[];
  listStyle: "table" | "cards";
  detailFields: string[];
  fieldLabels: Record<string, string>;
  help: Record<string, string>;
  fields: Record<string, { type: TFieldType; values?: string[] }>;
  references: Record<string, { summary: string; entity: string; href?: string | null }>;
  detail?: string | null;
  list?: string | null;
  /** The list operation that names this entity's records (a parent's name in a chart, a picker in 22.6). */
  listOperation?: string | null;
};

export type TFormField = {
  name: string;
  type: string;
  label?: string;
  required?: boolean;
  hidden?: boolean;
  value?: unknown;
  values?: string[];
  min?: number;
  max?: number;
  maxLength?: number;
  placeholder?: string;
};

export type TAppForm = {
  operationId: string;
  params?: Record<string, unknown>;
  load?: { operationId: string; params?: Record<string, unknown> };
  fields: TFormField[];
  submitLabel?: string;
  onSuccess?: { toast?: string; navigate?: string };
};

export type TAppError = { status: number; code: string; message: string; fields?: string[] };

export type TApp = {
  name: string;
  tagline: string | null;
  icon: string;
  home: string;
  density: "compact" | "comfortable";
  nav: TAppNavItem[];
  pages: Record<string, TAppPage>;
  routes: Record<string, string>;
  entities: Record<string, TAppEntity>;
  forms: Record<string, TAppForm>;
  errors: Record<string, TAppError[]>;
};

export type TRecord = Record<string, unknown> & { id?: unknown; allowedActions?: string[] };
export type TRouteParams = Record<string, string | string[] | undefined>;

/** The app's screens (`src/content/app.json`, generated from the FrontendSpec). */
export const app = data as unknown as TApp;

/** `$route.<name>` and `$record.<field>` become the route's parameter and the record's value. */
export function resolveValue(value: unknown, route: TRouteParams, record?: TRecord): unknown {
  if (typeof value !== "string") return value;
  if (value.startsWith("$route.")) {
    const found = route[value.slice("$route.".length)];
    return Array.isArray(found) ? found[0] : found;
  }
  if (value.startsWith("$record.") && record) return record[value.slice("$record.".length)];
  return value;
}

export function resolveParams(
  params: Record<string, unknown> | undefined,
  route: TRouteParams,
  record?: TRecord,
): Record<string, unknown> {
  return Object.fromEntries(Object.entries(params ?? {}).map(([name, value]) => [name, resolveValue(value, route, record)]));
}

/** A page's href: its route with `[param]` filled from the params (and `[id]` from the record or the route). */
export function pageHref(page: string, params: Record<string, unknown> = {}, route: TRouteParams = {}): string {
  const pattern = app.routes[page] ?? page;
  return pattern.replace(/\[([A-Za-z0-9_]+)\]/g, (_, name: string) => {
    const value = params[name] ?? resolveValue(`$route.${name}`, route);
    return encodeURIComponent(String(value ?? ""));
  });
}

/** Whether a record allows an action (Story 10.0b `allowedActions`): the backend decides, the kit only reads. Links
 *  that only show a record are always allowed; records without the list allow everything. */
export function allowed(record: TRecord | undefined, action: TAppAction): boolean {
  const list = record?.allowedActions;
  if (!Array.isArray(list)) return true;
  if (action.kind === "link") return action.id !== "edit" || list.includes("update");
  if (action.id === "delete") return list.includes("delete");
  return action.operationId ? list.includes(action.operationId) || list.includes(action.id) : true;
}

export function fieldLabel(entity: TAppEntity | undefined, field: string): string {
  const label = entity?.fieldLabels?.[field];
  if (label) return label;
  const words = field.replace(/([a-z0-9])([A-Z])/g, "$1 $2").replace(/_/g, " ");
  return words.charAt(0).toUpperCase() + words.slice(1).toLowerCase();
}

/** The name of a record: its display field, else its id. */
export function recordTitle(entity: TAppEntity | undefined, record: TRecord | undefined): string {
  if (!record) return "";
  const value = entity?.displayField ? record[entity.displayField] : undefined;
  return value === undefined || value === null || value === "" ? String(record.id ?? "") : String(value);
}

/** The records of a list response (`{items, total}`, or an array) and the total. */
export function listOf(response: unknown): { records: TRecord[]; total: number } {
  if (Array.isArray(response)) return { records: response as TRecord[], total: response.length };
  if (response && typeof response === "object" && Array.isArray((response as { items?: unknown }).items)) {
    const { items, total } = response as { items: TRecord[]; total?: number };
    return { records: items, total: typeof total === "number" ? total : items.length };
  }
  return { records: [], total: 0 };
}
