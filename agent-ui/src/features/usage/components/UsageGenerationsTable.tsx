import Link from "next/link";
import { ArrowDown, ArrowUp, ExternalLink, Waypoints } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { formatCostSplit, formatTokens } from "@/lib/format-usage";
import { StatusBadge } from "@/features/generations/components/StatusBadge";
import { formatDuration } from "@/features/generations/lib/status";
import type { TGenerationFilters, TGenerationSortKey, TUsageGeneration } from "../types";

type UsageGenerationsTableProps = {
  rows: TUsageGeneration[];
  options: { engines: string[]; modes: string[]; statuses: string[] };
  filters: TGenerationFilters;
  onFilter: (patch: Partial<TGenerationFilters>) => void;
  sort: { key: TGenerationSortKey; desc: boolean };
  onSort: (key: TGenerationSortKey) => void;
};

const dateFormat = new Intl.DateTimeFormat(undefined, { dateStyle: "medium", timeStyle: "short" });

const SORTABLE: { key: TGenerationSortKey; label: string }[] = [
  { key: "createdAt", label: "Created" },
  { key: "wallMs", label: "Duration" },
  { key: "modelCalls", label: "Model calls" },
  { key: "tokens", label: "Tokens in / out" },
  { key: "cost", label: "Cost" },
];

type FilterSelectProps = {
  label: string;
  value: string;
  values: string[];
  onChange: (value: string) => void;
};

function FilterSelect({ label, value, values, onChange }: FilterSelectProps) {
  const items = [{ value: "all", label: `All ${label}` }, ...values.map((item) => ({ value: item, label: item.toLowerCase() }))];
  return (
    <Select items={items} value={value} onValueChange={(next) => onChange(String(next))}>
      <SelectTrigger size="sm" className="w-40" aria-label={`Filter by ${label}`}>
        <SelectValue />
      </SelectTrigger>
      <SelectContent>
        {items.map((item) => (
          <SelectItem key={item.value} value={item.value}>
            {item.label}
          </SelectItem>
        ))}
      </SelectContent>
    </Select>
  );
}

export function UsageGenerationsTable({ rows, options, filters, onFilter, sort, onSort }: UsageGenerationsTableProps) {
  return (
    <div className="flex flex-col gap-3">
      <div className="flex flex-wrap items-center gap-2">
        <FilterSelect label="engines" value={filters.engine} values={options.engines} onChange={(engine) => onFilter({ engine })} />
        <FilterSelect label="modes" value={filters.mode} values={options.modes} onChange={(mode) => onFilter({ mode })} />
        <FilterSelect label="statuses" value={filters.status} values={options.statuses} onChange={(status) => onFilter({ status })} />
        <span className="text-sm text-muted-foreground">{rows.length} generation(s)</span>
      </div>
      <div className="rounded-lg border">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Project</TableHead>
              <TableHead>Mode</TableHead>
              <TableHead>Engine</TableHead>
              <TableHead>Status</TableHead>
              {SORTABLE.map((column) => (
                <TableHead key={column.key} className={column.key === "createdAt" ? undefined : "text-right"}>
                  <button
                    type="button"
                    className="inline-flex items-center gap-1 hover:text-foreground"
                    onClick={() => onSort(column.key)}
                  >
                    {column.label}
                    {sort.key === column.key && (sort.desc ? <ArrowDown className="size-3" /> : <ArrowUp className="size-3" />)}
                  </button>
                </TableHead>
              ))}
              <TableHead className="text-right">Trace</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {rows.map((row) => (
              <TableRow key={row.generationId}>
                <TableCell className="max-w-56 truncate font-medium">
                  <Link href={`/generations/${row.generationId}`} className="hover:underline">
                    {row.projectName ?? row.generationId}
                  </Link>
                </TableCell>
                <TableCell className="text-muted-foreground">{row.mode}</TableCell>
                <TableCell className="text-muted-foreground">{row.engine}</TableCell>
                <TableCell>
                  <StatusBadge status={row.status} />
                </TableCell>
                <TableCell className="text-muted-foreground tabular-nums">
                  {row.createdAt ? dateFormat.format(new Date(row.createdAt)) : "—"}
                </TableCell>
                <TableCell className="text-right tabular-nums">{row.wallMs != null ? formatDuration(row.wallMs) : "—"}</TableCell>
                <TableCell className="text-right tabular-nums">{row.modelCalls}</TableCell>
                <TableCell className="text-right tabular-nums">
                  {formatTokens(row.tokens.input)} / {formatTokens(row.tokens.output)}
                </TableCell>
                <TableCell className="text-right tabular-nums">{formatCostSplit(row.cost)}</TableCell>
                <TableCell className="text-right">
                  <div className="flex justify-end gap-1">
                    <Button
                      variant="ghost"
                      size="icon-sm"
                      aria-label="Open the trace"
                      render={<Link href={`/generations/${row.generationId}?tab=trace`} />}
                      nativeButton={false}
                    >
                      <Waypoints />
                    </Button>
                    {row.langsmithUrl && (
                      <Button
                        variant="ghost"
                        size="icon-sm"
                        aria-label="Open in LangSmith"
                        render={<a href={row.langsmithUrl} target="_blank" rel="noreferrer" />}
                        nativeButton={false}
                      >
                        <ExternalLink />
                      </Button>
                    )}
                  </div>
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </div>
    </div>
  );
}
