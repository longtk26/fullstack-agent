"use client";

import { Activity, ArrowUpRight, Clock, RefreshCw } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Tooltip, TooltipContent, TooltipTrigger } from "@/components/ui/tooltip";
import { Stack } from "@/components/layout/Stack";
import { cn } from "@/lib/utils";
import { usePreviewLogs } from "../../hooks/use-preview-logs";
import type { TPreviewRequest } from "../../types";

const METHOD_VARIANT: Record<string, "default" | "secondary" | "destructive" | "outline"> = {
  GET: "secondary",
  POST: "default",
  PUT: "outline",
  PATCH: "outline",
  DELETE: "destructive",
};

const METHOD_CLASS: Record<string, string> = {
  GET: "bg-info/15 text-info border-info/30",
  POST: "bg-success/15 text-success border-success/30",
  PUT: "bg-warning/15 text-warning border-warning/30",
  PATCH: "bg-warning/15 text-warning border-warning/30",
  DELETE: "bg-destructive/15 text-destructive border-destructive/30",
};

type AppNetworkPanelProps = {
  generationId: string;
  onOpenApiTab: (operationId?: string) => void;
  className?: string;
};

export function AppNetworkPanel({ generationId, onOpenApiTab, className }: AppNetworkPanelProps) {
  const { requests } = usePreviewLogs(generationId, true);
  const items: TPreviewRequest[] = requests.items ?? [];

  return (
    <div className={cn("flex flex-col h-full rounded-lg border bg-card overflow-hidden", className)}>
      <div className="flex items-center justify-between border-b px-3 py-2 bg-muted/30">
        <Stack direction="row" gap="xs" align="center">
          <Activity className="size-4 text-primary" />
          <h3 className="text-xs font-semibold">Network Calls</h3>
          <Badge variant="outline" className="text-[10px] tabular-nums font-mono">
            {items.length}
          </Badge>
        </Stack>
        <Tooltip>
          <TooltipTrigger render={<span />}>
            <Button
              size="sm"
              variant="ghost"
              className="size-6 p-0"
              onClick={() => requests.refetch()}
              disabled={requests.isFetching}
            >
              <RefreshCw className={cn("size-3", requests.isFetching && "animate-spin text-info")} />
            </Button>
          </TooltipTrigger>
          <TooltipContent>Refresh request log</TooltipContent>
        </Tooltip>
      </div>

      <ScrollArea className="flex-1">
        {items.length === 0 ? (
          <div className="flex flex-col items-center justify-center p-6 text-center text-muted-foreground">
            <Clock className="size-8 text-muted-foreground/40 mb-2" />
            <p className="text-xs font-medium">No API calls recorded</p>
            <p className="mt-1 text-[11px] text-muted-foreground/80 max-w-[200px]">
              Interact with the preview app or submit forms to see requests sent to the backend.
            </p>
          </div>
        ) : (
          <div className="divide-y divide-border/60">
            {items.map((req, idx) => {
              const method = req.method.toUpperCase();
              const is2xx = req.status >= 200 && req.status < 300;
              const is4xxOr5xx = req.status >= 400;

              return (
                <div
                  key={`${req.ts}-${idx}`}
                  className="p-2 text-xs hover:bg-muted/40 transition-colors flex flex-col gap-1"
                >
                  <div className="flex items-center justify-between gap-2">
                    <Stack direction="row" gap="xs" align="center" className="min-w-0">
                      <Badge
                        variant={METHOD_VARIANT[method] ?? "outline"}
                        className={cn("px-1.5 py-0 text-[10px] font-mono font-bold", METHOD_CLASS[method])}
                      >
                        {method}
                      </Badge>
                      <span className="font-mono text-[11px] truncate" title={req.path}>
                        {req.path}
                      </span>
                    </Stack>
                    <span
                      className={cn(
                        "font-mono text-[11px] font-semibold tabular-nums shrink-0",
                        is2xx && "text-success",
                        is4xxOr5xx && "text-destructive",
                        !is2xx && !is4xxOr5xx && "text-muted-foreground",
                      )}
                    >
                      {req.status}
                    </span>
                  </div>

                  <div className="flex items-center justify-between text-[11px] text-muted-foreground">
                    <span className="truncate">
                      {req.operationId ? (
                        <span className="font-medium text-foreground">{req.operationId}</span>
                      ) : (
                        <span className="italic">anonymous</span>
                      )}
                      {req.durationMs !== null && (
                        <span className="ml-1.5 tabular-nums">· {Math.round(req.durationMs)}ms</span>
                      )}
                    </span>

                    {req.operationId && (
                      <Button
                        size="xs"
                        variant="ghost"
                        className="h-5 px-1 text-[10px] text-primary hover:text-primary gap-0.5"
                        onClick={() => onOpenApiTab(req.operationId ?? undefined)}
                      >
                        Replay <ArrowUpRight className="size-2.5" />
                      </Button>
                    )}
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </ScrollArea>
    </div>
  );
}
