"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import { useVirtualizer } from "@tanstack/react-virtual";
import { eventCategory, type TEventCategory } from "../lib/event-format";
import type { TGenerationEvent, TLane } from "../types";

export const EVENT_ROW_HEIGHT = 32;

export const LANE_OPTIONS: { value: TLane | "all"; label: string }[] = [
  { value: "all", label: "All lanes" },
  { value: "backend", label: "Backend" },
  { value: "frontend", label: "Frontend" },
  { value: "integration", label: "Integration" },
];

export function useEventLog(events: TGenerationEvent[]) {
  const [category, setCategory] = useState<TEventCategory | "all">("all");
  const [lane, setLane] = useState<TLane | "all">("all");
  const [autoScroll, setAutoScroll] = useState(true);
  const scrollRef = useRef<HTMLDivElement>(null);

  const visible = useMemo(
    () =>
      events.filter((event) => {
        if (category !== "all" && eventCategory(event) !== category) return false;
        if (lane !== "all" && event.lane !== lane) return false;
        return true;
      }),
    [events, category, lane],
  );

  // eslint-disable-next-line react-hooks/incompatible-library -- TanStack Virtual returns non-memoizable functions
  const virtualizer = useVirtualizer({
    count: visible.length,
    getScrollElement: () => scrollRef.current,
    estimateSize: () => EVENT_ROW_HEIGHT,
    overscan: 12,
  });

  useEffect(() => {
    if (autoScroll && visible.length > 0) virtualizer.scrollToIndex(visible.length - 1, { align: "end" });
  }, [autoScroll, visible.length, virtualizer]);

  return { category, setCategory, lane, setLane, autoScroll, setAutoScroll, scrollRef, visible, virtualizer };
}
