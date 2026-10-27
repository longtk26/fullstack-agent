"use client";

import { useMemo, useState } from "react";
import { useSearchParams } from "next/navigation";
import { deriveNodeStates } from "../lib/node-states";
import type { TDetailTab } from "../types";
import { useGeneration, useWorkflowGraph } from "./use-generation";
import { useGenerationStream } from "./use-generation-stream";

const DETAIL_TABS: TDetailTab[] = ["steps", "trace", "results", "api"];

export function useGenerationDetail(id: string) {
  const detail = useGeneration(id);
  const graph = useWorkflowGraph();
  const { events, state: streamState } = useGenerationStream(id);
  const requestedTab = useSearchParams().get("tab");
  const [tab, setTab] = useState<TDetailTab>(() =>
    DETAIL_TABS.includes(requestedTab as TDetailTab) ? (requestedTab as TDetailTab) : "steps",
  );
  const [selectedNode, setSelectedNode] = useState<string | null>(null);

  const status = detail.data?.status;
  const progress = useMemo(() => deriveNodeStates(events, status), [events, status]);
  const repairAttempts = useMemo(
    () => Math.max(detail.data?.repairAttempts ?? 0, progress.repair_code?.attempts ?? 0),
    [detail.data?.repairAttempts, progress],
  );

  return {
    detail,
    graph: graph.data,
    events,
    streamState,
    progress,
    repairAttempts,
    maxRepairAttempts: detail.data?.options.maxRepairAttempts ?? 3,
    tab,
    setTab,
    selectedNode,
    setSelectedNode,
  };
}
