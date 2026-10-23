"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import { useVirtualizer } from "@tanstack/react-virtual";
import { eventCategory, type TEventCategory } from "../lib/event-format";
import type { TGenerationEvent } from "../types";

export const EVENT_ROW_HEIGHT = 32;

export function useEventLog(events: TGenerationEvent[]) {
  const [category, setCategory] = useState<TEventCategory | "all">("all");
  const [autoScroll, setAutoScroll] = useState(true);
  const scrollRef = useRef<HTMLDivElement>(null);

  const visible = useMemo(
    () => (category === "all" ? events : events.filter((event) => eventCategory(event) === category)),
    [events, category],
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

  return { category, setCategory, autoScroll, setAutoScroll, scrollRef, visible, virtualizer };
}
