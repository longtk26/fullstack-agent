"use client";

import { ChevronLeft, ChevronRight, Inbox, Plus, Search, TriangleAlert } from "lucide-react";
import Link from "next/link";
import { usePathname, useParams, useRouter, useSearchParams } from "next/navigation";
import { Suspense, useEffect, useState } from "react";
import { Button, buttonVariants } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Empty, EmptyContent, EmptyDescription, EmptyHeader, EmptyMedia, EmptyTitle } from "@/components/ui/empty";
import { Input } from "@/components/ui/input";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Skeleton } from "@/components/ui/skeleton";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { cn } from "@/lib/utils";
import {
  enumLabel,
  app,
  fieldLabel,
  listOf,
  pageHref,
  recordTitle,
  resolveParams,
  type TAppAction,
  type TAppEntity,
  type TAppSection,
  type TRecord,
  type TRouteParams,
} from "./app";
import { filterOptions, useOperationQuery } from "./bindings";
import { FieldValue } from "./FieldValue";
import { RowActions } from "./RecordActions";

const PAGE_SIZE = 20;
const RECENT = 5;

type ListProps = { section: TAppSection; heading: "h1" | "h2"; pageId: string; hideTitle?: boolean };

/** The list parameters in the URL, per section (`<section>.q`, `.page`…), so two lists on a page do not share them. */
function useListState(sectionId: string) {
  const searchParams = useSearchParams();
  const router = useRouter();
  const pathname = usePathname();
  const key = (name: string) => `${sectionId}.${name}`;
  const get = (name: string) => searchParams?.get(key(name)) ?? null;
  function set(changes: Record<string, string | null>) {
    const next = new URLSearchParams(searchParams?.toString() ?? "");
    for (const [name, value] of Object.entries(changes)) {
      if (value === null || value === "") next.delete(key(name));
      else next.set(key(name), value);
    }
    if (!("page" in changes)) next.delete(key("page"));
    const query = next.toString();
    router.replace(query ? `${pathname}?${query}` : pathname, { scroll: false });
  }
  return { get, set };
}

function Controls({ section, entity, state }: { section: TAppSection; entity?: TAppEntity; state: ReturnType<typeof useListState> }) {
  const controls = section.content?.controls ?? {};
  const [search, setSearch] = useState(state.get("q") ?? "");
  const options = filterOptions[section.data?.operationId ?? ""] ?? {};
  useEffect(() => {
    const timer = setTimeout(() => {
      if (search !== (state.get("q") ?? "")) state.set({ q: search || null });
    }, 300);
    return () => clearTimeout(timer);
  }, [search]); // eslint-disable-line react-hooks/exhaustive-deps
  const filters = (controls.filters ?? []).filter((name) => options[name]?.length);
  if (!controls.search && filters.length === 0 && !controls.sort?.length) return null;
  return (
    <div className="flex flex-wrap items-center gap-2" role="search">
      {controls.search && (
        <div className="relative min-w-48 flex-1 sm:max-w-xs">
          <Search className="pointer-events-none absolute top-1/2 left-2.5 size-4 -translate-y-1/2 text-muted-foreground" aria-hidden />
          <Input
            type="search"
            value={search}
            onChange={(event) => setSearch(event.target.value)}
            placeholder={`Search ${(entity?.plural ?? "records").toLowerCase()}`}
            aria-label={`Search ${(entity?.plural ?? "records").toLowerCase()}`}
            className="pl-8"
          />
        </div>
      )}
      {filters.map((name) => (
        <Select
          key={name}
          items={{ ALL: `All: ${fieldLabel(entity, name).toLowerCase()}`, ...Object.fromEntries(options[name].map((o) => [o, enumLabel(o)])) }}
          value={state.get(name) ?? "ALL"}
          onValueChange={(value) => state.set({ [name]: value === "ALL" || value === null ? null : String(value) })}
        >
          <SelectTrigger className="w-40" aria-label={fieldLabel(entity, name)}>
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="ALL">All: {fieldLabel(entity, name).toLowerCase()}</SelectItem>
            {options[name].map((option) => (
              <SelectItem key={option} value={option}>
                {enumLabel(option)}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      ))}
      {Boolean(controls.sort?.length) && (
        <Select
          items={{
            DEFAULT: "Default order",
            ...Object.fromEntries(
              (controls.sort ?? []).flatMap((field) => [
                [field, `${fieldLabel(entity, field)} ↑`],
                [`-${field}`, `${fieldLabel(entity, field)} ↓`],
              ]),
            ),
          }}
          value={state.get("sort") ?? "DEFAULT"}
          onValueChange={(value) => state.set({ sort: value === "DEFAULT" || value === null ? null : String(value) })}
        >
          <SelectTrigger className="w-44" aria-label="Sort">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="DEFAULT">Default order</SelectItem>
            {(controls.sort ?? []).flatMap((field) => [
              <SelectItem key={field} value={field}>
                {fieldLabel(entity, field)} ↑
              </SelectItem>,
              <SelectItem key={`-${field}`} value={`-${field}`}>
                {fieldLabel(entity, field)} ↓
              </SelectItem>,
            ])}
          </SelectContent>
        </Select>
      )}
    </div>
  );
}

function Pager({ page, total, size, onPage }: { page: number; total: number; size: number; onPage: (page: number) => void }) {
  const pages = Math.max(1, Math.ceil(total / size));
  if (pages <= 1) return null;
  return (
    <nav className="flex items-center justify-between gap-2 text-sm text-muted-foreground" aria-label="Pages">
      <span>
        {(page - 1) * size + 1}–{Math.min(page * size, total)} of {total}
      </span>
      <div className="flex items-center gap-1">
        <Button variant="outline" size="icon-sm" onClick={() => onPage(page - 1)} disabled={page <= 1} aria-label="Previous page">
          <ChevronLeft aria-hidden />
        </Button>
        <span className="px-2 tabular-nums">
          {page} / {pages}
        </span>
        <Button variant="outline" size="icon-sm" onClick={() => onPage(page + 1)} disabled={page >= pages} aria-label="Next page">
          <ChevronRight aria-hidden />
        </Button>
      </div>
    </nav>
  );
}

function CreateLink({ section }: { section: TAppSection }) {
  const route = (useParams() ?? {}) as TRouteParams;
  const create = section.content?.create;
  if (!create) return null;
  return (
    <Link
      href={pageHref(create.page, resolveParams(create.params, route), route)}
      className={cn(buttonVariants({ size: "sm" }))}
      data-bga-action="create"
    >
      <Plus aria-hidden />
      {create.label}
    </Link>
  );
}

function viewHref(actions: TAppAction[], record: TRecord, route: TRouteParams): string | undefined {
  const view = actions.find((action) => action.id === "view" && action.page);
  return view?.page ? pageHref(view.page, resolveParams(view.params, route, record), route) : undefined;
}

function Rows({ section, entity, records }: { section: TAppSection; entity?: TAppEntity; records: TRecord[] }) {
  const route = (useParams() ?? {}) as TRouteParams;
  const router = useRouter();
  const fields = section.data?.fields ?? [];
  const actions = section.content?.actions ?? [];
  const compact = app.density === "compact";
  if ((section.content?.style ?? entity?.listStyle) === "cards") {
    return (
      <ul className="grid gap-3 sm:grid-cols-2 xl:grid-cols-3">
        {records.map((record) => {
          const href = viewHref(actions, record, route);
          const title = recordTitle(entity, record);
          return (
            <li key={String(record.id)}>
              <Card size="sm" className="h-full">
                <CardHeader className="flex flex-row items-start justify-between gap-2">
                  <CardTitle className="min-w-0 truncate">
                    {href ? (
                      <Link href={href} className="underline-offset-4 hover:underline">
                        {title}
                      </Link>
                    ) : (
                      title
                    )}
                  </CardTitle>
                  <RowActions actions={actions} record={record} label={title} />
                </CardHeader>
                <CardContent>
                  <dl className="grid grid-cols-[auto_1fr] gap-x-3 gap-y-1 text-sm">
                    {fields
                      .filter((field) => field !== entity?.displayField)
                      .map((field) => (
                        <div key={field} className="contents">
                          <dt className="text-muted-foreground">{fieldLabel(entity, field)}</dt>
                          <dd className="min-w-0 truncate">
                            <FieldValue entity={entity} field={field} record={record} />
                          </dd>
                        </div>
                      ))}
                  </dl>
                </CardContent>
              </Card>
            </li>
          );
        })}
      </ul>
    );
  }
  return (
    <div className="overflow-x-auto rounded-lg border">
      <Table>
        <TableHeader>
          <TableRow>
            {fields.map((field) => (
              <TableHead key={field}>{fieldLabel(entity, field)}</TableHead>
            ))}
            {actions.length > 0 && <TableHead className="w-12 text-right"><span className="sr-only">Actions</span></TableHead>}
          </TableRow>
        </TableHeader>
        <TableBody>
          {records.map((record) => {
            const href = viewHref(actions, record, route);
            return (
              <TableRow
                key={String(record.id)}
                className={cn(href && "cursor-pointer", compact && "[&_td]:py-1.5")}
                onClick={(event) => {
                  if (!href || (event.target as HTMLElement).closest("a,button,[role=menuitem]")) return;
                  router.push(href);
                }}
              >
                {fields.map((field, index) => (
                  <TableCell key={field} className={cn(index === 0 && "font-medium")}>
                    {index === 0 && href && !entity?.references?.[field] ? (
                      <Link href={href} className="underline-offset-4 hover:underline">
                        <FieldValue entity={entity} field={field} record={record} link={false} />
                      </Link>
                    ) : (
                      <FieldValue entity={entity} field={field} record={record} />
                    )}
                  </TableCell>
                ))}
                {actions.length > 0 && (
                  <TableCell className="text-right">
                    <RowActions actions={actions} record={record} label={recordTitle(entity, record)} />
                  </TableCell>
                )}
              </TableRow>
            );
          })}
        </TableBody>
      </Table>
    </div>
  );
}

export function ListSkeleton({ rows = 5 }: { rows?: number }) {
  return (
    <div className="flex flex-col gap-2" aria-busy="true" aria-label="Loading">
      {Array.from({ length: rows }, (_, index) => (
        <Skeleton key={index} className="h-10 w-full" />
      ))}
    </div>
  );
}

export function LoadError({ onRetry }: { onRetry: () => void }) {
  return (
    <Empty className="border border-destructive/30">
      <EmptyHeader>
        <EmptyMedia variant="icon">
          <TriangleAlert aria-hidden />
        </EmptyMedia>
        <EmptyTitle>Could not load this</EmptyTitle>
        <EmptyDescription>Check the connection and try again.</EmptyDescription>
      </EmptyHeader>
      <EmptyContent>
        <Button variant="outline" size="sm" onClick={onRetry}>
          Try again
        </Button>
      </EmptyContent>
    </Empty>
  );
}

function ListBody({ section, heading, hideTitle }: ListProps) {
  const route = (useParams() ?? {}) as TRouteParams;
  const state = useListState(section.id);
  const entity = app.entities[section.content?.entity ?? ""];
  const recent = section.content?.variant === "recent";
  const controls = section.content?.controls ?? {};
  const page = Math.max(1, Number(state.get("page") ?? 1) || 1);
  const size = recent ? RECENT : PAGE_SIZE;
  const params: Record<string, unknown> = { ...resolveParams(section.data?.params, route) };
  if (!recent) {
    if (controls.search && state.get("q")) params.q = state.get("q");
    for (const name of controls.filters ?? []) if (state.get(name)) params[name] = state.get(name);
    if (state.get("sort")) params.sort = state.get("sort");
    if (section.data?.action === "list") Object.assign(params, { limit: size, offset: (page - 1) * size });
  }
  const query = useOperationQuery(section.data?.operationId, params);
  const { records, total } = listOf(query.data);
  const title = section.content?.title ?? entity?.plural ?? "Records";
  const Heading = heading;
  const filtered = Boolean(state.get("q")) || (controls.filters ?? []).some((name) => state.get(name));

  return (
    <div className="flex flex-col gap-4">
      <div className={cn("flex flex-wrap items-center justify-between gap-3", hideTitle && !section.content?.create && "sr-only")}>
        <Heading
          className={cn(heading === "h1" ? "text-2xl font-semibold tracking-tight" : "text-lg font-semibold", hideTitle && "sr-only")}
        >
          {title}
        </Heading>
        <CreateLink section={section} />
      </div>
      {!recent && <Controls section={section} entity={entity} state={state} />}
      {query.isLoading ? (
        <ListSkeleton rows={recent ? 3 : 5} />
      ) : query.error ? (
        <LoadError onRetry={() => query.refetch()} />
      ) : records.length === 0 ? (
        <Empty className="border">
          <EmptyHeader>
            <EmptyMedia variant="icon">
              <Inbox aria-hidden />
            </EmptyMedia>
            <EmptyTitle>{filtered ? "Nothing matches" : `No ${title.toLowerCase()} yet`}</EmptyTitle>
            <EmptyDescription>
              {filtered ? "Try another search or filter." : section.content?.create ? "Add the first one." : "They appear here once added."}
            </EmptyDescription>
          </EmptyHeader>
          {!filtered && section.content?.create && (
            <EmptyContent>
              <CreateLink section={section} />
            </EmptyContent>
          )}
        </Empty>
      ) : (
        <>
          <Rows section={section} entity={entity} records={records} />
          {!recent && section.data?.action === "list" && (
            <Pager page={page} total={total} size={size} onPage={(next) => state.set({ page: String(next) })} />
          )}
        </>
      )}
    </div>
  );
}

/** The records of an entity (Story 22.4): a table (or cards) bound to its list operation, with search, filters, sort
 *  and pages on the server, row actions in a menu, and loading, empty and error states. */
export function AppList(props: ListProps) {
  return (
    <Suspense fallback={<ListSkeleton />}>
      <ListBody {...props} />
    </Suspense>
  );
}
