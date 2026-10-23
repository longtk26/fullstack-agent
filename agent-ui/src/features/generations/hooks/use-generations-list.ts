"use client";

import { useState } from "react";
import { useGenerations } from "./use-generations";
import type { TGenerationStatus } from "../types";

export type TStatusFilter = TGenerationStatus | "ALL";

/** List state: a status filter plus a stack of cursors so "Previous" can walk back. */
export function useGenerationsList() {
  const [status, setStatus] = useState<TStatusFilter>("ALL");
  const [cursors, setCursors] = useState<string[]>([]);
  const cursor = cursors.at(-1);
  const query = useGenerations({ status: status === "ALL" ? undefined : status, cursor });

  return {
    query,
    status,
    page: cursors.length + 1,
    changeStatus: (next: TStatusFilter) => {
      setStatus(next);
      setCursors([]);
    },
    hasPrevious: cursors.length > 0,
    hasNext: Boolean(query.data?.nextCursor),
    previous: () => setCursors((stack) => stack.slice(0, -1)),
    next: () => {
      const nextCursor = query.data?.nextCursor;
      if (nextCursor) setCursors((stack) => [...stack, nextCursor]);
    },
  };
}
