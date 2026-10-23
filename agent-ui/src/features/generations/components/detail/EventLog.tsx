"use client";

import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Switch } from "@/components/ui/switch";
import { Stack } from "@/components/layout/Stack";
import { useEventLog } from "../../hooks/use-event-log";
import { EVENT_CATEGORIES, type TEventCategory } from "../../lib/event-format";
import type { TGenerationEvent } from "../../types";
import { EventRow } from "./EventRow";

type EventLogProps = {
  events: TGenerationEvent[];
};

export function EventLog({ events }: EventLogProps) {
  const { category, setCategory, autoScroll, setAutoScroll, scrollRef, visible, virtualizer } = useEventLog(events);

  return (
    <Stack gap="sm">
      <Stack direction="row" justify="between" align="center" wrap className="gap-y-2">
        <h2 className="text-sm font-medium">
          Event log <span className="text-muted-foreground">({visible.length})</span>
        </h2>
        <Stack direction="row" gap="md" align="center">
          <Select
            items={EVENT_CATEGORIES}
            value={category}
            onValueChange={(value) => setCategory(value as TEventCategory | "all")}
          >
            <SelectTrigger size="sm" className="w-36" aria-label="Filter events">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              {EVENT_CATEGORIES.map((option) => (
                <SelectItem key={option.value} value={option.value}>
                  {option.label}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
          <Label className="flex items-center gap-2 text-xs font-normal">
            <Switch size="sm" checked={autoScroll} onCheckedChange={setAutoScroll} />
            Auto-scroll
          </Label>
        </Stack>
      </Stack>
      <div ref={scrollRef} className="h-[680px] overflow-auto rounded-lg border bg-card">
        {visible.length === 0 ? (
          <p className="p-4 text-sm text-muted-foreground">Waiting for events…</p>
        ) : (
          <div className="relative w-full" style={{ height: virtualizer.getTotalSize() }}>
            {virtualizer.getVirtualItems().map((item) => (
              <div
                key={visible[item.index].id}
                className="absolute top-0 left-0 w-full border-b border-border/50"
                style={{ height: item.size, transform: `translateY(${item.start}px)` }}
              >
                <EventRow event={visible[item.index]} />
              </div>
            ))}
          </div>
        )}
      </div>
    </Stack>
  );
}
