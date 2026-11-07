"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { useSearchParams } from "next/navigation";
import { deriveNodeStates } from "../lib/node-states";
import type { TDetailTab } from "../types";
import { useGeneration, useWorkflowGraph } from "./use-generation";
import { useGenerationStream } from "./use-generation-stream";

const DETAIL_TABS: TDetailTab[] = ["steps", "trace", "results", "api", "app", "business"];

export function useGenerationDetail(id: string) {
  const detail = useGeneration(id);
  const graph = useWorkflowGraph(detail.data?.mode);
  const { events, state: streamState } = useGenerationStream(id);
  const requestedTab = useSearchParams().get("tab");
  const [tab, setTab] = useState<TDetailTab>(() =>
    DETAIL_TABS.includes(requestedTab as TDetailTab) ? (requestedTab as TDetailTab) : "steps",
  );
  const [selectedNode, setSelectedNode] = useState<string | null>(null);
  const autoSwitchedRef = useRef(false);
  const userPickedRef = useRef(false);
  const selectTab = useCallback((next: TDetailTab) => {
    userPickedRef.current = true;
    setTab(next);
  }, []);

  const status = detail.data?.status;
  const progress = useMemo(() => deriveNodeStates(events, status), [events, status]);
  const repairAttempts = useMemo(
    () => Math.max(detail.data?.repairAttempts ?? 0, progress.repair_code?.attempts ?? 0),
    [detail.data?.repairAttempts, progress],
  );
  const frontendRepairAttempts = useMemo(
    () => progress.repair_frontend?.attempts ?? 0,
    [progress],
  );

  // Story 9.9 / Q13: v0-style hand-off to the App tab. Story 18.12: as soon as the frontend preview first runs,
  // even while the backend is still being generated; once, and never after the user picked a tab.
  useEffect(() => {
    if (autoSwitchedRef.current || userPickedRef.current || requestedTab) return;
    const mode = detail.data?.mode;
    if (mode !== "static" && mode !== "dynamic") return;

    if (detail.data?.frontendPreview?.status === "RUNNING") {
      autoSwitchedRef.current = true;
      const timer = setTimeout(() => setTab("app"), 0);
      return () => clearTimeout(timer);
    }
  }, [detail.data?.mode, detail.data?.frontendPreview?.status, requestedTab]);

  return {
    detail,
    graph: graph.data,
    events,
    streamState,
    progress,
    repairAttempts,
    frontendRepairAttempts,
    maxRepairAttempts: detail.data?.options.maxRepairAttempts ?? 3,
    tab,
    setTab: selectTab,
    selectedNode,
    setSelectedNode,
  };
}
