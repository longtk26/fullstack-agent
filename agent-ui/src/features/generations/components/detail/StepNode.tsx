"use client";

import { Handle, Position } from "@xyflow/react";
import type { Node, NodeProps } from "@xyflow/react";
import { Ban, CircleCheck, CircleDashed, CircleX, Loader2, SkipForward } from "lucide-react";
import type { LucideIcon } from "lucide-react";
import { cn } from "@/lib/utils";
import type { TNodeState } from "../../lib/node-states";

export type TStepNodeData = {
  label: string;
  state: TNodeState;
  attempts: number;
  selected: boolean;
  terminal: boolean;
};

export type TStepFlowNode = Node<TStepNodeData, "step">;

/** Invisible corner markers, so fitting the view also covers edges dagre routed outside the node bounds. */
export type TBoundsFlowNode = Node<Record<string, never>, "bounds">;

export function BoundsNode() {
  return <div className="size-px" />;
}

const STATE_STYLE: Record<TNodeState, { icon: LucideIcon; className: string }> = {
  pending: { icon: CircleDashed, className: "border-border text-muted-foreground" },
  running: { icon: Loader2, className: "border-info bg-info/10 text-foreground ring-4 ring-info/20" },
  passed: { icon: CircleCheck, className: "border-success/60 bg-success/10 text-foreground" },
  failed: { icon: CircleX, className: "border-destructive/60 bg-destructive/10 text-foreground" },
  skipped: { icon: SkipForward, className: "border-dashed border-border text-muted-foreground" },
  cancelled: { icon: Ban, className: "border-border bg-muted text-muted-foreground" },
};

const ICON_TONE: Record<TNodeState, string> = {
  pending: "text-muted-foreground",
  running: "animate-spin text-info",
  passed: "text-success",
  failed: "text-destructive",
  skipped: "text-muted-foreground",
  cancelled: "text-muted-foreground",
};

export function StepNode({ data }: NodeProps<TStepFlowNode>) {
  const { icon: Icon, className } = STATE_STYLE[data.state];
  return (
    <div
      className={cn(
        "flex items-center gap-2 border bg-card text-sm shadow-xs transition-all",
        data.terminal ? "h-8 w-[72px] justify-center rounded-full text-xs" : "h-12 w-[200px] rounded-lg px-3",
        className,
        data.selected && "outline-2 outline-offset-2 outline-ring",
        !data.terminal && "cursor-pointer",
      )}
    >
      <Handle type="target" position={Position.Top} className="opacity-0" isConnectable={false} />
      {!data.terminal && <Icon className={cn("size-4 shrink-0", ICON_TONE[data.state])} />}
      <span className={cn("truncate", !data.terminal && "font-medium")}>{data.label.replaceAll("_", " ")}</span>
      {data.attempts > 1 && (
        <span className="ml-auto rounded-full bg-muted px-1.5 text-xs text-muted-foreground tabular-nums">
          ×{data.attempts}
        </span>
      )}
      <Handle type="source" position={Position.Bottom} className="opacity-0" isConnectable={false} />
    </div>
  );
}
