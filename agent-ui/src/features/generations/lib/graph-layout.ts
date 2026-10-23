import { Graph, layout } from "@dagrejs/dagre";
import type { TWorkflowGraph } from "../types";
import { END_NODE, START_NODE } from "./node-states";

export const STEP_NODE_SIZE = { width: 200, height: 48 };
export const TERMINAL_NODE_SIZE = { width: 72, height: 32 };
const LABEL_CHAR_WIDTH = 6;
const LABEL_HEIGHT = 16;

export type TPoint = { x: number; y: number };
export type TEdgeRoute = { points: TPoint[]; label: TPoint | null };
export type TGraphLayout = {
  nodes: Record<string, TPoint>;
  edges: Record<string, TEdgeRoute>;
  size: { width: number; height: number };
};

export function isTerminalNode(id: string): boolean {
  return id === START_NODE || id === END_NODE;
}

export function edgeId(source: string, target: string): string {
  return `${source}->${target}`;
}

/**
 * Top-to-bottom dagre layout. Node positions are top-left (as React Flow expects); edges keep dagre's
 * routed points, which bend around nodes, and a reserved spot for their label.
 */
export function layoutGraph(graph: TWorkflowGraph, labelFor: (source: string, target: string) => string | null) {
  const g = new Graph();
  g.setGraph({ rankdir: "TB", nodesep: 40, ranksep: 28, edgesep: 16 });
  for (const node of graph.nodes) {
    // dagre writes x/y onto the label object, so each node needs its own copy.
    g.setNode(node.id, { ...(isTerminalNode(node.id) ? TERMINAL_NODE_SIZE : STEP_NODE_SIZE) });
  }
  for (const edge of graph.edges) {
    const label = labelFor(edge.source, edge.target);
    g.setEdge(
      edge.source,
      edge.target,
      label ? { width: label.length * LABEL_CHAR_WIDTH, height: LABEL_HEIGHT, labelpos: "c" } : {},
    );
  }
  layout(g);

  const { width = 0, height = 0 } = g.graph();
  const result: TGraphLayout = { nodes: {}, edges: {}, size: { width, height } };
  for (const node of graph.nodes) {
    const { x, y, width, height } = g.node(node.id);
    result.nodes[node.id] = { x: x - width / 2, y: y - height / 2 };
  }
  for (const edge of graph.edges) {
    const routed = g.edge(edge.source, edge.target) as { points?: TPoint[]; x?: number; y?: number };
    result.edges[edgeId(edge.source, edge.target)] = {
      points: routed.points ?? [],
      label: routed.x !== undefined && routed.y !== undefined ? { x: routed.x, y: routed.y } : null,
    };
  }
  return result;
}

/** A polyline through the points with rounded bends (quadratic curves at each inner point). */
export function roundedPath(points: TPoint[]): string {
  if (points.length === 0) return "";
  let path = `M ${points[0].x},${points[0].y}`;
  for (let i = 1; i < points.length - 1; i += 1) {
    const next = points[i + 1];
    path += ` Q ${points[i].x},${points[i].y} ${(points[i].x + next.x) / 2},${(points[i].y + next.y) / 2}`;
  }
  const last = points[points.length - 1];
  return `${path} L ${last.x},${last.y}`;
}
