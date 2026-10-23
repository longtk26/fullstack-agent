"use client";

import { useCallback, useMemo } from "react";
import { MarkerType } from "@xyflow/react";
import type { TRoutedFlowEdge } from "../components/detail/RoutedEdge";
import type { TBoundsFlowNode, TStepFlowNode } from "../components/detail/StepNode";
import { edgeId, isTerminalNode, layoutGraph } from "../lib/graph-layout";
import { REPAIR_NODE, VALIDATION_NODE, type TNodeProgress } from "../lib/node-states";
import type { TWorkflowGraph } from "../types";

type TDiagramInput = {
  graph: TWorkflowGraph | undefined;
  progress: Record<string, TNodeProgress>;
  selectedNode: string | null;
  repairAttempts: number;
  maxRepairAttempts: number;
};

function boundsNodes({ width, height }: { width: number; height: number }): TBoundsFlowNode[] {
  return [
    { id: "__bounds_start", position: { x: 0, y: 0 } },
    { id: "__bounds_end", position: { x: width - 1, y: height - 1 } },
  ].map((node) => ({ ...node, type: "bounds", data: {}, draggable: false, selectable: false, focusable: false }));
}

/** Turns the API graph plus live node progress into React Flow nodes and routed edges. */
export function useWorkflowDiagram({ graph, progress, selectedNode, repairAttempts, maxRepairAttempts }: TDiagramInput) {
  const labelFor = useCallback(
    (source: string, target: string) => {
      const label = graph?.edges.find((edge) => edge.source === source && edge.target === target)?.label ?? null;
      if (source === VALIDATION_NODE && target === REPAIR_NODE) {
        return `${label ?? "failed"} · attempt ${repairAttempts} / ${maxRepairAttempts}`;
      }
      return label;
    },
    [graph, repairAttempts, maxRepairAttempts],
  );
  const layout = useMemo(() => (graph ? layoutGraph(graph, labelFor) : null), [graph, labelFor]);

  const nodes = useMemo<(TStepFlowNode | TBoundsFlowNode)[]>(
    () => [
      ...(graph?.nodes ?? []).map<TStepFlowNode>((node) => ({
        id: node.id,
        type: "step",
        position: layout?.nodes[node.id] ?? { x: 0, y: 0 },
        draggable: false,
        selectable: !isTerminalNode(node.id),
        data: {
          label: node.label,
          state: progress[node.id]?.state ?? "pending",
          attempts: progress[node.id]?.attempts ?? 0,
          selected: node.id === selectedNode,
          terminal: isTerminalNode(node.id),
        },
      })),
      ...(layout ? boundsNodes(layout.size) : []),
    ],
    [graph, layout, progress, selectedNode],
  );

  const edges = useMemo<TRoutedFlowEdge[]>(
    () =>
      (graph?.edges ?? []).map((edge) => {
        const id = edgeId(edge.source, edge.target);
        const targetRunning = progress[edge.target]?.state === "running";
        const traversed = progress[edge.source]?.state === "passed" && progress[edge.target] !== undefined;
        return {
          id,
          type: "routed",
          source: edge.source,
          target: edge.target,
          markerEnd: { type: MarkerType.ArrowClosed, width: 14, height: 14 },
          data: {
            route: layout?.edges[id] ?? { points: [], label: null },
            text: labelFor(edge.source, edge.target),
            conditional: edge.conditional,
            active: traversed || targetRunning,
          },
        };
      }),
    [graph, layout, progress, labelFor],
  );

  return { nodes, edges };
}
