import { http, HttpResponse, type HttpHandler } from "msw";
import { MOCK_API_BASE } from "@/lib/api/client";
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
  mock?: "record" | "records" | "merge" | "create" | "sample" | null;
  sample?: unknown;
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

function notFound(entity: string | null) {
  return HttpResponse.json({ error: { code: "NOT_FOUND", message: `${entity ?? "Record"} not found`, details: null } }, { status: 404 });
}

function compare(a: unknown, b: unknown): number {
  if (a === b) return 0;
  if (a === null || a === undefined) return 1;
  if (b === null || b === undefined) return -1;
  return String(a).localeCompare(String(b), undefined, { numeric: true });
}

function list(op: TMockOperation, url: URL) {
  let items = [...records(op.entity)];
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
  const paged = items.slice(offset, offset + limit);
  if (op.envelope === false) {
    return HttpResponse.json(paged);
  }
  return HttpResponse.json({ items: paged, total: items.length, limit, offset });
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
    if (op.action === "list" || op.mock === "records") return list(op, url);
    if (op.action === "get" || op.mock === "record") return find() ? HttpResponse.json(find()) : notFound(op.entity);
    if (op.action === "create" || op.mock === "create") {
      const body = ((await request.json().catch(() => ({}))) || {}) as TRecord;
      const created = { [op.primaryKey]: newId(op.entity, op.primaryKey), createdAt: new Date().toISOString(), ...body };
      records(op.entity).push(created);
      return HttpResponse.json(created, { status: op.status });
    }
    if (op.action === "update") {
      const current = find();
      if (!current) return notFound(op.entity);
      Object.assign(current, (await request.json()) as TRecord);
      return HttpResponse.json(current);
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
      return HttpResponse.json(current, { status: op.status });
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
