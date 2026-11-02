"use client";

import { usePathname, useRouter, useSearchParams } from "next/navigation";
import { Suspense, useCallback, useState, type ReactNode } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { filterOptions } from "@/components/renderer/bindings";
import type { TBinding, TColumn, TRecord, TSectionControls } from "@/components/renderer/site";
import {
  controlParams,
  useSectionRecords,
  type TSectionRecords,
} from "@/components/renderer/use-section-records";

type TSearchParams = ReturnType<typeof useSearchParams>;

type SectionControlsProps = {
  controls?: TSectionControls;
  columns?: TColumn[];
  total?: number;
  operationId?: string;
  records?: TRecord[];
  searchParams: TSearchParams;
};

/** A filter's values: the contract's enum when it has one, else the values seen in the loaded records. */
function useFilterValues(filters: string[], operationId: string | undefined, records: TRecord[]) {
  const known = (operationId && filterOptions[operationId]) || {};
  const [seen, setSeen] = useState<Record<string, string[]>>({});
  const loaded: Record<string, string[]> = {};
  let grew = false;
  for (const field of filters) {
    if (known[field]?.length) continue;
    const values = new Set(seen[field] ?? []);
    for (const record of records) {
      const value = record[field];
      if (value !== undefined && value !== null && value !== "" && typeof value !== "object") {
        if (!values.has(String(value))) grew = true;
        values.add(String(value));
      }
    }
    loaded[field] = [...values].sort();
  }
  if (grew) setSeen({ ...seen, ...loaded });
  return (field: string) => (known[field]?.length ? known[field] : (loaded[field] ?? []));
}

function optionLabel(value: string) {
  const words = value.replace(/[_-]+/g, " ").trim().toLowerCase();
  return words ? words[0].toUpperCase() + words.slice(1) : value;
}

/** Search, filters, sort and pagination for a data section; they live in the URL's search params. */
export function SectionControls({ controls, columns = [], total, operationId, records = [], searchParams }: SectionControlsProps) {
  const router = useRouter();
  const pathname = usePathname();

  const currentQ = searchParams?.get("q") ?? "";
  const [searchValue, setSearchValue] = useState(currentQ);
  const [prevQ, setPrevQ] = useState(currentQ);

  if (currentQ !== prevQ) {
    setPrevQ(currentQ);
    setSearchValue(currentQ);
  }

  const updateParam = useCallback(
    (key: string, value: string | null) => {
      const next = new URLSearchParams(searchParams?.toString() ?? "");
      if (value && value !== "ALL") {
        next.set(key, value);
      } else {
        next.delete(key);
      }
      if (key !== "page" && key !== "offset") {
        next.delete("page");
        next.delete("offset");
      }
      const query = next.toString();
      router.replace(query ? `${pathname}?${query}` : pathname, { scroll: false });
    },
    [pathname, router, searchParams],
  );

  const filters = controls?.filters ?? [];
  const filterValues = useFilterValues(filters, operationId, records);

  if (!controls) return null;

  const pageSize = controls.pageSize ?? 10;
  const currentPage = Number(searchParams?.get("page") ?? 1) || 1;
  const totalPages = total !== undefined ? Math.max(1, Math.ceil(total / pageSize)) : undefined;

  const hasSearch = Boolean(controls.search);
  const sortOptions = controls.sort ?? [];
  const hasSort = sortOptions.length > 0;
  const hasFilters = filters.length > 0;
  const hasPagination = totalPages !== undefined && totalPages > 1;

  if (!hasSearch && !hasFilters && !hasSort && !hasPagination) return null;

  const columnByKey = Object.fromEntries(columns.map((c) => [c.key, c]));

  return (
    <div className="flex flex-col gap-3 py-2 sm:flex-row sm:items-center sm:justify-between">
      <div className="flex flex-1 flex-wrap items-center gap-2">
        {hasSearch && (
          <form
            onSubmit={(e) => {
              e.preventDefault();
              updateParam("q", searchValue.trim() || null);
            }}
            className="flex items-center gap-1.5"
          >
            <Input
              type="search"
              placeholder="Search…"
              value={searchValue}
              onChange={(e) => setSearchValue(e.target.value)}
              onBlur={() => updateParam("q", searchValue.trim() || null)}
              className="h-8 w-44 sm:w-60"
            />
          </form>
        )}

        {filters.map((field) => {
          const col = columnByKey[field];
          const label = col?.label ?? field;
          const currentVal = searchParams?.get(field) ?? "ALL";
          const values = filterValues(field);
          const options = currentVal !== "ALL" && !values.includes(currentVal) ? [...values, currentVal] : values;
          return (
            <Select
              key={field}
              value={currentVal}
              onValueChange={(val) => updateParam(field, val)}
            >
              <SelectTrigger className="h-8 w-36 text-xs">
                <SelectValue placeholder={`Filter ${label}`} />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="ALL">All {label}</SelectItem>
                {options.map((option) => (
                  <SelectItem key={option} value={option}>
                    {optionLabel(option)}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          );
        })}

        {hasSort && (
          <Select
            value={searchParams?.get("sort") ?? "DEFAULT"}
            onValueChange={(val) => updateParam("sort", val === "DEFAULT" ? null : val)}
          >
            <SelectTrigger className="h-8 w-36 text-xs">
              <SelectValue placeholder="Sort by…" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="DEFAULT">Default sort</SelectItem>
              {sortOptions.map((opt) => {
                const label = columnByKey[opt.replace(/^-/, "").replace(/:.*$/, "")]?.label ?? opt;
                return (
                  <SelectItem key={opt} value={opt}>
                    {label}
                  </SelectItem>
                );
              })}
            </SelectContent>
          </Select>
        )}
      </div>

      {hasPagination && (
        <div className="flex items-center gap-2 text-xs text-muted-foreground">
          <span>
            Page {currentPage} of {totalPages}
          </span>
          <Button
            variant="outline"
            size="sm"
            className="h-7 px-2"
            disabled={currentPage <= 1}
            onClick={() => updateParam("page", String(currentPage - 1))}
          >
            Previous
          </Button>
          <Button
            variant="outline"
            size="sm"
            className="h-7 px-2"
            disabled={currentPage >= (totalPages ?? 1)}
            onClick={() => updateParam("page", String(currentPage + 1))}
          >
            Next
          </Button>
        </div>
      )}
    </div>
  );
}

type ControlledRecordsProps = {
  items?: TRecord[];
  binding?: TBinding;
  controls?: TSectionControls;
  columns?: TColumn[];
  /** The section's body: its records, and the controls bar to show above them (null without controls). */
  children: (result: TSectionRecords, controlsBar: ReactNode) => ReactNode;
};

function Records({ items, binding, controls, children }: ControlledRecordsProps) {
  const result = useSectionRecords(items, binding, controlParams(controls, null));
  return <>{children(result, null)}</>;
}

function UrlRecords({ items, binding, controls, columns, children }: ControlledRecordsProps) {
  const searchParams = useSearchParams();
  const result = useSectionRecords(items, binding, controlParams(controls, searchParams));
  const controlsBar = (
    <SectionControls
      controls={controls}
      columns={columns}
      total={result.total}
      operationId={binding?.operationId}
      records={result.records}
      searchParams={searchParams}
    />
  );
  return <>{children(result, controlsBar)}</>;
}

/**
 * A data section's records with its controls. Only a section with `controls` reads the URL's search params, inside
 * its own `<Suspense>` whose fallback renders the first page unfiltered, so the static export keeps every page's
 * records in its HTML.
 */
export function ControlledRecords(props: ControlledRecordsProps) {
  if (!props.controls) return <Records {...props} />;
  return (
    <Suspense fallback={<Records {...props} />}>
      <UrlRecords {...props} />
    </Suspense>
  );
}
