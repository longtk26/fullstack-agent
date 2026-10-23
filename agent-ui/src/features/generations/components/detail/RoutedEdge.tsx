"use client";

import { BaseEdge, EdgeLabelRenderer } from "@xyflow/react";
import type { Edge, EdgeProps } from "@xyflow/react";
import { cn } from "@/lib/utils";
import { roundedPath, type TEdgeRoute } from "../../lib/graph-layout";

export type TRoutedEdgeData = {
  route: TEdgeRoute;
  text: string | null;
  conditional: boolean;
  active: boolean;
};

export type TRoutedFlowEdge = Edge<TRoutedEdgeData, "routed">;

/** Draws the path dagre routed (it bends around nodes) instead of a straight handle-to-handle curve. */
export function RoutedEdge({ id, data, markerEnd }: EdgeProps<TRoutedFlowEdge>) {
  if (!data) return null;
  return (
    <>
      <BaseEdge
        id={id}
        path={roundedPath(data.route.points)}
        markerEnd={markerEnd}
        className={cn(data.active ? "bga-edge-active" : "bga-edge", data.conditional && "bga-edge-conditional")}
      />
      {data.text && data.route.label && (
        <EdgeLabelRenderer>
          <div
            className="nodrag nopan pointer-events-none absolute rounded bg-card px-1 text-[10px] whitespace-nowrap text-muted-foreground"
            style={{ transform: `translate(-50%, -50%) translate(${data.route.label.x}px, ${data.route.label.y}px)` }}
          >
            {data.text}
          </div>
        </EdgeLabelRenderer>
      )}
    </>
  );
}
