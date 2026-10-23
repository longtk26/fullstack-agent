import { Activity } from "lucide-react";
import { cn } from "@/lib/utils";
import { describeEvent, EVENT_ICONS, eventTime, isProblem } from "../../lib/event-format";
import type { TGenerationEvent } from "../../types";

type EventRowProps = {
  event: TGenerationEvent;
  showStep?: boolean;
};

export function EventRow({ event, showStep = true }: EventRowProps) {
  const Icon = EVENT_ICONS[event.type] ?? Activity;
  return (
    <div
      className={cn(
        "flex h-8 items-center gap-2 px-3 text-xs",
        isProblem(event) && "text-destructive",
        event.type === "engine.event" && "text-muted-foreground",
      )}
    >
      <span className="w-16 shrink-0 font-mono text-muted-foreground tabular-nums">{eventTime(event)}</span>
      <Icon className="size-3.5 shrink-0" />
      {showStep && (
        <span className="w-32 shrink-0 truncate text-muted-foreground">{event.step?.replaceAll("_", " ") ?? "—"}</span>
      )}
      <span className="min-w-0 truncate" title={describeEvent(event)}>
        {describeEvent(event)}
      </span>
    </div>
  );
}
