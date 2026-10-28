"use client";

import { useEffect } from "react";
import { Background, Controls, ReactFlow, useNodesInitialized, useReactFlow } from "@xyflow/react";
import { useTheme } from "next-themes";
import { Skeleton } from "@/components/ui/skeleton";
import { useWorkflowDiagram } from "../../hooks/use-workflow-diagram";
import { isTerminalNode } from "../../lib/graph-layout";
import type { TNodeProgress } from "../../lib/node-states";
import type { TWorkflowGraph } from "../../types";
import { RoutedEdge } from "./RoutedEdge";
import { BoundsNode, StepNode } from "./StepNode";

const NODE_TYPES = { step: StepNode, bounds: BoundsNode };
const EDGE_TYPES = { routed: RoutedEdge };
const FIT_OPTIONS = { padding: 0.08 };

/** Re-fits once nodes are measured and whenever the layout changes (the `fitView` prop only fits once). */
function FitOnLayout({ layoutKey }: { layoutKey: string }) {
  const { fitView } = useReactFlow();
  const initialized = useNodesInitialized();
  useEffect(() => {
    if (initialized) fitView(FIT_OPTIONS);
  }, [initialized, layoutKey, fitView]);
  return null;
}

type WorkflowDiagramProps = {
  graph: TWorkflowGraph | undefined;
  progress: Record<string, TNodeProgress>;
  selectedNode: string | null;
  onSelectNode: (node: string) => void;
  repairAttempts: number;
  frontendRepairAttempts?: number;
  maxRepairAttempts: number;
};

export function WorkflowDiagram({ graph, onSelectNode, ...input }: WorkflowDiagramProps) {
  const { resolvedTheme } = useTheme();
  const { nodes, edges } = useWorkflowDiagram({ graph, ...input });

  if (!graph) return <Skeleton className="h-[720px] w-full" />;

  return (
    <div className="bga-flow h-[720px] w-full overflow-hidden rounded-lg border bg-card">
      <ReactFlow
        nodes={nodes}
        edges={edges}
        nodeTypes={NODE_TYPES}
        edgeTypes={EDGE_TYPES}
        colorMode={resolvedTheme === "dark" ? "dark" : "light"}
        onNodeClick={(_, node) => node.type === "step" && !isTerminalNode(node.id) && onSelectNode(node.id)}
        nodesConnectable={false}
        nodesDraggable={false}
        fitView
        fitViewOptions={FIT_OPTIONS}
        proOptions={{ hideAttribution: true }}
        minZoom={0.4}
        maxZoom={1.5}
      >
        <Background gap={16} />
        <Controls showInteractive={false} />
        <FitOnLayout layoutKey={`${nodes.length}:${input.repairAttempts}`} />
      </ReactFlow>
    </div>
  );
}
