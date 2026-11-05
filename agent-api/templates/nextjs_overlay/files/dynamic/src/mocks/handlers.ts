import { http, HttpResponse, type HttpHandler } from "msw";
import { MOCK_API_BASE } from "@/lib/api/client";
import entities from "./entities.json";
import fixtures from "./fixtures.json";
import operations from "./operations.json";

/** Generic mock API built from the contract (operations.json) and its example records (fixtures.json): lists
 *  honour limit, offset, sort, filters and q; writes change an in-memory store until the page reloads. */
type TMockOperation = {
  operationId: string;
  method: string;
  path: string;
  entity: string | null;
  action: string | null;
  mock?: "record" | "records" | "merge" | "create" | "sample" | "aggregate" | null;
  sample?: unknown;
  /** Epic 21: an aggregate operation, computed here from the fixtures as the backend computes it from its table. */
  aggregate?: { fn: string; field?: string; groupBy?: string; period?: string; dateField?: string; filters?: Record<string, unknown> } | null;
  envelope?: boolean;
  primaryKey: string;
  status: number;
  filters: string[];
  sort: string[];
  search: boolean;
  defaultLimit: number;
  maxLimit: number;
};

type TRecord = Record<string, unknown>;

/** Story 10.0b: what the API adds to a stored record (`x-bga.entities` of the contract). */
type TEntityInfo = {
  primaryKey: string;
  labelField: string | null;
  references?: { field: string; apiName: string; entity: string; labelField: string | null }[];
  allowedActions?: string[];
  secretFields?: string[];
};

const presentation = entities as Record<string, TEntityInfo>;

const seed = fixtures as Record<string, TRecord[]>;
let store: Record<string, TRecord[]> = structuredClone(seed);

export function resetMockStore() {
  store = structuredClone(seed);
}

function records(entity: string | null): TRecord[] {
  if (!entity) return [];
  store[entity] ??= [];
  return store[entity];
}

/** A record as the API answers it: each parent as `{id, label}`, and what can be done to it (Story 10.0b). */
function present(entity: string | null, record: TRecord): TRecord {
  const info = entity ? presentation[entity] : undefined;
  if (!info) return record;
  if (!info.allowedActions) {
    const out: TRecord = { ...record };
    for (const field of info.secretFields ?? []) delete out[field]; // a password hash never leaves the backend
    return out;
  }
  const out: TRecord = { ...record, allowedActions: [...info.allowedActions] };
  for (const field of info.secretFields ?? []) delete out[field]; // a password hash never leaves the backend
  for (const ref of info.references ?? []) {
    const id = record[ref.field];
    const key = presentation[ref.entity]?.primaryKey ?? "id";
    const parent = records(ref.entity).find((item) => String(item[key]) === String(id));
    out[ref.apiName] = id === null || id === undefined ? null : { id, label: parent && ref.labelField ? (parent[ref.labelField] ?? null) : null };
  }
  return out;
}

function notFound(entity: string | null) {
  return HttpResponse.json({ error: { code: "NOT_FOUND", message: `${entity ?? "Record"} not found`, details: null } }, { status: 404 });
}

function compare(a: unknown, b: unknown): number {
  if (a === b) return 0;
  if (a === null || a === undefined) return 1;
  if (b === null || b === undefined) return -1;
  return String(a).localeCompare(String(b), undefined, { numeric: true });
}

function list(op: TMockOperation, url: URL, params: Record<string, unknown> = {}) {
  let items = [...records(op.entity)];
  // A list scoped by its path (`/fields/:fieldId/reviews`) keeps the records of that parent.
  for (const [name, value] of Object.entries(params)) {
    if (typeof value === "string" && items.some((it) => name in it)) items = items.filter((item) => String(item[name]) === value);
  }
  for (const [name, value] of url.searchParams.entries()) {
    if (!value || ["limit", "offset", "sort", "q"].includes(name)) continue;
    if (name.endsWith("Before")) {
      const field = name.slice(0, -"Before".length);
      items = items.filter((item) => {
        const v = item[field];
        return v !== undefined && v !== null && String(v) <= value;
      });
    } else if (name.endsWith("After")) {
      const field = name.slice(0, -"After".length);
      items = items.filter((item) => {
        const v = item[field];
        return v !== undefined && v !== null && String(v) >= value;
      });
    } else if (op.filters.includes(name) || items.some((it) => name in it)) {
      items = items.filter((item) => String(item[name]) === value);
    }
  }
  const query = url.searchParams.get("q");
  if (op.search && query) {
    const needle = query.toLowerCase();
    items = items.filter((item) => Object.values(item).some((value) => typeof value === "string" && value.toLowerCase().includes(needle)));
  }
  const sort = url.searchParams.get("sort");
  if (sort) {
    const field = sort.replace(/^-/, "");
    if (!op.sort.includes(field)) {
      return HttpResponse.json({ error: { code: "VALIDATION_ERROR", message: `Cannot sort by ${field}`, details: null } }, { status: 422 });
    }
    const direction = sort.startsWith("-") ? -1 : 1;
    items.sort((a, b) => direction * compare(a[field], b[field]));
  }
  const limit = Math.min(Number(url.searchParams.get("limit") ?? op.defaultLimit) || op.defaultLimit, op.maxLimit);
  const offset = Number(url.searchParams.get("offset") ?? 0) || 0;
  const paged = items.slice(offset, offset + limit).map((item) => present(op.entity, item));
  if (op.envelope === false) {
    return HttpResponse.json(paged);
  }
  return HttpResponse.json({ items: paged, total: items.length, limit, offset });
}

/** `fn` of `field` over `rows` (count needs none), optionally grouped and limited to the current period. */
function aggregate(
  spec: NonNullable<TMockOperation["aggregate"]>,
  rows: TRecord[],
): { value: number } | { key: string; value: number }[] {
  const now = new Date();
  const since: Record<string, Date> = {
    day: new Date(now.getFullYear(), now.getMonth(), now.getDate()),
    week: new Date(now.getTime() - 7 * 86_400_000),
    month: new Date(now.getFullYear(), now.getMonth(), 1),
    year: new Date(now.getFullYear(), 0, 1),
  };
  let items = rows.filter((row) => Object.entries(spec.filters ?? {}).every(([name, value]) => String(row[name]) === String(value)));
  if (spec.period && since[spec.period]) {
    const dateField = spec.dateField ?? Object.keys(items[0] ?? {}).find((key) => /date|at$/i.test(key));
    if (dateField) items = items.filter((row) => new Date(String(row[dateField])) >= since[spec.period as string]);
  }
  const measure = (group: TRecord[]): number => {
    if (spec.fn === "count") return group.length;
    const values = group.map((row) => Number(row[spec.field ?? ""])).filter((value) => Number.isFinite(value));
    if (values.length === 0) return 0;
    if (spec.fn === "sum") return values.reduce((a, b) => a + b, 0);
    if (spec.fn === "avg") return values.reduce((a, b) => a + b, 0) / values.length;
    if (spec.fn === "min") return Math.min(...values);
    return Math.max(...values);
  };
  if (!spec.groupBy) return { value: measure(items) };
  const groups = new Map<string, TRecord[]>();
  for (const row of items) {
    const key = String(row[spec.groupBy] ?? "—");
    groups.set(key, [...(groups.get(key) ?? []), row]);
  }
  return Array.from(groups, ([key, group]) => ({ key, value: measure(group) }));
}

function newId(entity: string | null, primaryKey: string): string | number {
  const existing = records(entity);
  const numeric = existing.length > 0 && typeof existing[0][primaryKey] === "number";
  return numeric ? Math.max(0, ...existing.map((item) => Number(item[primaryKey]))) + 1 : crypto.randomUUID();
}

function handler(op: TMockOperation): HttpHandler {
  const route = `*${MOCK_API_BASE}${op.path}`;
  const method = op.method.toLowerCase() as "get" | "post" | "put" | "patch" | "delete";
  return http[method](route, async ({ request, params }) => {
    const url = new URL(request.url);
    const id = params.id ?? params[op.primaryKey];
    const find = () => records(op.entity).find((item) => String(item[op.primaryKey]) === String(id));
    if (op.mock === "aggregate" && op.aggregate) return HttpResponse.json(aggregate(op.aggregate, records(op.entity)));
    const sample = op.sample;
    if (op.action === "list" && op.mock === "sample" && Array.isArray(sample)) {
      // A custom list with its own record shape: the entity's records (when it has any) over the sample's fields.
      const rows = records(op.entity);
      const first = (sample[0] ?? {}) as Record<string, unknown>;
      return HttpResponse.json(rows.length ? rows.map((row) => ({ ...first, ...row })) : sample);
    }
    if (op.action === "list" || op.mock === "records") return list(op, url, op.action === "list" ? params : {});
    if (op.action === "get" || op.mock === "record") {
      const found = find();
      return found ? HttpResponse.json(present(op.entity, found)) : notFound(op.entity);
    }
    if (op.action === "create" || op.mock === "create") {
      const body = ((await request.json().catch(() => ({}))) || {}) as TRecord;
      const created = { [op.primaryKey]: newId(op.entity, op.primaryKey), createdAt: new Date().toISOString(), ...body };
      records(op.entity).push(created);
      return HttpResponse.json(present(op.entity, created), { status: op.status });
    }
    if (op.action === "update") {
      const current = find();
      if (!current) return notFound(op.entity);
      Object.assign(current, (await request.json()) as TRecord);
      return HttpResponse.json(present(op.entity, current));
    }
    if (op.mock === "merge") {
      const current = find();
      if (!current) return notFound(op.entity);
      const body = ((await request.json().catch(() => ({}))) || {}) as TRecord;
      for (const [k, v] of Object.entries(body)) {
        if (v !== undefined) {
          current[k] = v;
        }
      }
      return HttpResponse.json(present(op.entity, current), { status: op.status });
    }
    if (op.mock === "sample") {
      if (op.status === 204) return new HttpResponse(null, { status: 204 });
      return HttpResponse.json(op.sample ?? {}, { status: op.status });
    }
    if (op.action === "delete") {
      const current = find();
      if (!current) return notFound(op.entity);
      store[op.entity as string] = records(op.entity).filter((item) => item !== current);
      return new HttpResponse(null, { status: 204 });
    }
    console.warn(`[MSW] ${op.operationId} has no mock plan`);
    return HttpResponse.json({ error: { code: "NOT_IMPLEMENTED", message: `${op.operationId} has no mock`, details: null } }, { status: 501 });
  });
}

export const handlers: HttpHandler[] = (operations as TMockOperation[]).map(handler);
