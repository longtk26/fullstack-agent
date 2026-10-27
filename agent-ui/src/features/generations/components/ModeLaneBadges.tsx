import { Globe, Layers, Server } from "lucide-react";
import type { LucideIcon } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Tooltip, TooltipContent, TooltipTrigger } from "@/components/ui/tooltip";
import { cn } from "@/lib/utils";
import type { TGenerationMode, TLane, TLanes, TLaneStatus } from "../types";

const MODE: Record<TGenerationMode, { icon: LucideIcon; label: string; hint: string }> = {
  backend: { icon: Server, label: "API", hint: "Backend API only" },
  static: { icon: Globe, label: "Static", hint: "Static website: pages only, no backend" },
  dynamic: { icon: Layers, label: "Dynamic", hint: "Web app: frontend and backend from one API contract" },
};

const LANE_ORDER: TLane[] = ["backend", "frontend", "integration"];

const LANE_DOT: Record<TLaneStatus, string> = {
  PENDING: "bg-muted-foreground/40",
  RUNNING: "bg-info animate-pulse",
  VALIDATING: "bg-info",
  REPAIRING: "bg-warning",
  COMPLETED: "bg-success",
  FAILED: "bg-destructive",
  SKIPPED: "bg-muted-foreground/40",
};

type ModeLaneBadgesProps = {
  mode: TGenerationMode;
  lanes: TLanes;
  /** One dot per lane instead of a badge each (tables). */
  compact?: boolean;
  className?: string;
};

/** Mode badge plus one badge per lane (Story 12.2); a backend-only job has one lane, so its status says it all. */
export function ModeLaneBadges({ mode, lanes, compact = false, className }: ModeLaneBadgesProps) {
  const { icon: Icon, label, hint } = MODE[mode] ?? MODE.backend;
  const shown = mode === "backend" ? [] : LANE_ORDER.filter((lane) => lanes[lane]);
  return (
    <span className={cn("inline-flex flex-wrap items-center gap-1", className)}>
      <Tooltip>
        <TooltipTrigger render={<span />}>
          <Badge variant="outline">
            <Icon /> {label}
          </Badge>
        </TooltipTrigger>
        <TooltipContent>{hint}</TooltipContent>
      </Tooltip>
      {compact && shown.length > 0 && (
        <Tooltip>
          <TooltipTrigger render={<span className="inline-flex items-center gap-1 px-1" />}>
            {shown.map((lane) => (
              <span
                key={lane}
                className={cn("size-2 rounded-full", LANE_DOT[lanes[lane] as TLaneStatus])}
                aria-label={`${lane} ${lanes[lane]?.toLowerCase()}`}
              />
            ))}
          </TooltipTrigger>
          <TooltipContent>
            {shown.map((lane) => (
              <div key={lane}>
                {lane}: {lanes[lane]?.toLowerCase()}
              </div>
            ))}
          </TooltipContent>
        </Tooltip>
      )}
      {!compact && shown.map((lane) => {
        const status = lanes[lane] as TLaneStatus;
        return (
          <Badge key={lane} variant="outline" className={cn("font-normal", status === "SKIPPED" && "text-muted-foreground")}>
            <span className={cn("size-1.5 rounded-full", LANE_DOT[status])} aria-hidden />
            {lane} · {status.toLowerCase()}
          </Badge>
        );
      })}
    </span>
  );
}
