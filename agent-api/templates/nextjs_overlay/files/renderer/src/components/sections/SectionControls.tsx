"use client";

import { usePathname, useRouter, useSearchParams } from "next/navigation";
import { useCallback, useState } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import type { TColumn, TSectionControls } from "@/components/renderer/site";

type SectionControlsProps = {
  controls?: TSectionControls;
  columns?: TColumn[];
  total?: number;
  recordsCount?: number;
};

export function SectionControls({ controls, columns = [], total }: SectionControlsProps) {
  const router = useRouter();
  const pathname = usePathname();
  const searchParams = useSearchParams();

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

  if (!controls) return null;

  const pageSize = controls.pageSize ?? 10;
  const currentPage = Number(searchParams?.get("page") ?? 1) || 1;
  const totalPages = total !== undefined ? Math.max(1, Math.ceil(total / pageSize)) : undefined;

  const hasSearch = Boolean(controls.search);
  const filters = controls.filters ?? [];
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
                <SelectItem value="TODO">TODO</SelectItem>
                <SelectItem value="IN_PROGRESS">In Progress</SelectItem>
                <SelectItem value="DONE">Done</SelectItem>
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
