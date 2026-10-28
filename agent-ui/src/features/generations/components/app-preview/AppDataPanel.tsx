"use client";

import { useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Database, Eye, RefreshCw, Table as TableIcon } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { ScrollArea } from "@/components/ui/scroll-area";
import {
  Sheet,
  SheetContent,
  SheetDescription,
  SheetHeader,
  SheetTitle,
} from "@/components/ui/sheet";
import { Tooltip, TooltipContent, TooltipTrigger } from "@/components/ui/tooltip";
import { Stack } from "@/components/layout/Stack";
import { cn } from "@/lib/utils";
import { useResults } from "../../hooks/use-results";
import type { TGenerationDetail } from "../../types";

type TableData = {
  name: string;
  path: string;
  operationId: string;
  count: number | null;
  items: unknown[];
  error?: string | null;
};

type AppDataPanelProps = {
  detail: TGenerationDetail;
  className?: string;
};

export function AppDataPanel({ detail, className }: AppDataPanelProps) {
  const { manifest } = useResults(detail);
  const backendUrl = detail.preview?.url;
  const isBackendRunning = detail.preview?.status === "RUNNING" && Boolean(backendUrl);

  const [viewingTable, setViewingTable] = useState<TableData | null>(null);

  // Derive candidate list endpoints from manifest
  const candidateEndpoints = useMemo(() => {
    if (!manifest.data) return [];
    const ops = manifest.data.operations ?? [];
    // List endpoints are GET methods that don't take dynamic path parameters
    return ops
      .filter((op) => op.method.toLowerCase() === "get" && !op.path.includes("{"))
      .map((op) => {
        // Derive friendly entity name from module or path
        const segments = op.path.split("/").filter(Boolean);
        const lastSegment = segments[segments.length - 1] || "items";
        const name = lastSegment
          .replaceAll("-", " ")
          .replaceAll("_", " ")
          .replace(/\b\w/g, (c) => c.toUpperCase());

        return {
          name,
          path: op.path,
          operationId: op.operationId,
        };
      });
  }, [manifest.data]);

  const {
    data: tables = [],
    isFetching,
    refetch,
  } = useQuery<TableData[]>({
    queryKey: [
      "app-preview-tables",
      detail.generationId,
      backendUrl,
      candidateEndpoints.map((c) => c.path),
    ],
    queryFn: async () => {
      if (!backendUrl || !isBackendRunning || candidateEndpoints.length === 0) return [];
      return await Promise.all(
        candidateEndpoints.map(async (ep) => {
          try {
            const res = await fetch(`${backendUrl}${ep.path}`, {
              headers: { Accept: "application/json" },
            });
            if (!res.ok) {
              return {
                name: ep.name,
                path: ep.path,
                operationId: ep.operationId,
                count: null,
                items: [],
                error: `HTTP ${res.status}`,
              };
            }
            const json = await res.json();
            let count = 0;
            let items: unknown[] = [];
            if (Array.isArray(json)) {
              count = json.length;
              items = json;
            } else if (json && Array.isArray(json.items)) {
              count = json.items.length;
              items = json.items;
            } else if (json && Array.isArray(json.data)) {
              count = json.data.length;
              items = json.data;
            }

            return {
              name: ep.name,
              path: ep.path,
              operationId: ep.operationId,
              count,
              items,
            };
          } catch {
            return {
              name: ep.name,
              path: ep.path,
              operationId: ep.operationId,
              count: null,
              items: [],
              error: "Failed to connect",
            };
          }
        }),
      );
    },
    enabled: isBackendRunning && candidateEndpoints.length > 0,
    refetchInterval: 5000,
  });

  return (
    <div className={cn("flex flex-col h-full rounded-lg border bg-card overflow-hidden", className)}>
      <div className="flex items-center justify-between border-b px-3 py-2 bg-muted/30">
        <Stack direction="row" gap="xs" align="center">
          <Database className="size-4 text-primary" />
          <h3 className="text-xs font-semibold">Backend Tables</h3>
          <Badge variant="outline" className="text-[10px] tabular-nums font-mono">
            {tables.length}
          </Badge>
        </Stack>
        <Tooltip>
          <TooltipTrigger render={<span />}>
            <Button
              size="sm"
              variant="ghost"
              className="size-6 p-0"
              onClick={() => refetch()}
              disabled={isFetching || !isBackendRunning}
            >
              <RefreshCw className={cn("size-3", isFetching && "animate-spin text-info")} />
            </Button>
          </TooltipTrigger>
          <TooltipContent>Refresh table rows</TooltipContent>
        </Tooltip>
      </div>

      <ScrollArea className="flex-1">
        {!isBackendRunning ? (
          <div className="flex flex-col items-center justify-center p-6 text-center text-muted-foreground">
            <Database className="size-8 text-muted-foreground/40 mb-2" />
            <p className="text-xs font-medium">Backend preview not running</p>
            <p className="mt-1 text-[11px] text-muted-foreground/80 max-w-[200px]">
              Start the backend preview container to view table data and records.
            </p>
          </div>
        ) : tables.length === 0 ? (
          <div className="flex flex-col items-center justify-center p-6 text-center text-muted-foreground">
            <TableIcon className="size-8 text-muted-foreground/40 mb-2" />
            <p className="text-xs font-medium">Discovering tables…</p>
          </div>
        ) : (
          <div className="divide-y divide-border/60">
            {tables.map((tbl) => (
              <div
                key={tbl.path}
                className="flex items-center justify-between p-2.5 text-xs hover:bg-muted/40 transition-colors"
              >
                <div className="min-w-0 pr-2">
                  <div className="flex items-center gap-1.5 font-medium text-foreground truncate">
                    <TableIcon className="size-3.5 text-muted-foreground shrink-0" />
                    <span className="truncate">{tbl.name}</span>
                  </div>
                  <p className="font-mono text-[11px] text-muted-foreground truncate">{tbl.path}</p>
                </div>

                <div className="flex items-center gap-2 shrink-0">
                  {tbl.error ? (
                    <Badge variant="outline" className="text-[10px] text-muted-foreground">
                      {tbl.error}
                    </Badge>
                  ) : (
                    <Badge
                      variant={tbl.count && tbl.count > 0 ? "secondary" : "outline"}
                      className={cn(
                        "text-[11px] tabular-nums font-mono",
                        tbl.count && tbl.count > 0 && "bg-primary/10 text-primary",
                      )}
                    >
                      {tbl.count === null ? "—" : `${tbl.count} row${tbl.count === 1 ? "" : "s"}`}
                    </Badge>
                  )}

                  {tbl.items.length > 0 && (
                    <Tooltip>
                      <TooltipTrigger render={<span />}>
                        <Button
                          size="xs"
                          variant="ghost"
                          className="size-6 p-0"
                          onClick={() => setViewingTable(tbl)}
                        >
                          <Eye className="size-3" />
                        </Button>
                      </TooltipTrigger>
                      <TooltipContent>View records</TooltipContent>
                    </Tooltip>
                  )}
                </div>
              </div>
            ))}
          </div>
        )}
      </ScrollArea>

      {/* Record viewer sheet */}
      <Sheet open={Boolean(viewingTable)} onOpenChange={(open: boolean) => !open && setViewingTable(null)}>
        <SheetContent side="right" className="data-[side=right]:w-full data-[side=right]:sm:max-w-xl flex flex-col">
          <SheetHeader>
            <SheetTitle className="flex items-center gap-2 text-base">
              <TableIcon className="size-4 text-primary" /> {viewingTable?.name} Records
              <Badge variant="outline" className="font-mono text-xs tabular-nums">
                {viewingTable?.count} row{viewingTable?.count === 1 ? "" : "s"}
              </Badge>
            </SheetTitle>
            <SheetDescription className="font-mono text-xs text-muted-foreground">
              {viewingTable?.path}
            </SheetDescription>
          </SheetHeader>
          <div className="flex-1 overflow-auto rounded-md border bg-muted/40 p-3 font-mono text-xs mt-4">
            <pre className="whitespace-pre-wrap">
              {JSON.stringify(viewingTable?.items ?? [], null, 2)}
            </pre>
          </div>
        </SheetContent>
      </Sheet>
    </div>
  );
}
