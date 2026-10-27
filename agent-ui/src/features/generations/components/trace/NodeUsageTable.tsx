import { ArrowDown, ArrowUp } from "lucide-react";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { formatCostSplit, formatPercent, formatTokens } from "@/lib/format-usage";
import type { TNodeUsage } from "@/types/usage";
import type { TNodeSortKey } from "../../hooks/use-trace-view";
import { formatDuration, formatStep } from "../../lib/status";

type NodeUsageTableProps = {
  nodes: TNodeUsage[];
  sort: { key: TNodeSortKey; desc: boolean };
  onSort: (key: TNodeSortKey) => void;
};

const COLUMNS: { key: TNodeSortKey; label: string; numeric?: boolean }[] = [
  { key: "node", label: "Node" },
  { key: "attempts", label: "Runs", numeric: true },
  { key: "durationMs", label: "Duration", numeric: true },
  { key: "modelCalls", label: "Model calls", numeric: true },
  { key: "tokens", label: "Tokens in / out", numeric: true },
  { key: "cost", label: "Cost", numeric: true },
];

type ShareBarProps = {
  part: number;
  whole: number;
  label: string;
};

function ShareBar({ part, whole, label }: ShareBarProps) {
  const share = whole > 0 ? part / whole : 0;
  return (
    <div className="flex items-center gap-2" title={`${formatPercent(part, whole)} of ${label}`}>
      <div className="h-1.5 w-16 overflow-hidden rounded-full bg-muted">
        <div className="h-full rounded-full bg-chart-1" style={{ width: `${Math.round(share * 100)}%` }} />
      </div>
      <span className="w-8 text-right text-xs text-muted-foreground tabular-nums">{formatPercent(part, whole)}</span>
    </div>
  );
}

/** Per-node summary (Story 9.4): where time and money went, with each node's share of both. */
export function NodeUsageTable({ nodes, sort, onSort }: NodeUsageTableProps) {
  const totalMs = nodes.reduce((sum, node) => sum + node.durationMs, 0);
  const totalCost = nodes.reduce((sum, node) => sum + node.cost.total, 0);
  return (
    <div className="rounded-lg border">
      <Table>
        <TableHeader>
          <TableRow>
            {COLUMNS.map((column) => (
              <TableHead key={column.key} className={column.numeric ? "text-right" : undefined}>
                <button
                  type="button"
                  className="inline-flex items-center gap-1 hover:text-foreground"
                  onClick={() => onSort(column.key)}
                >
                  {column.label}
                  {sort.key === column.key && (sort.desc ? <ArrowDown className="size-3" /> : <ArrowUp className="size-3" />)}
                </button>
              </TableHead>
            ))}
            <TableHead>Share of time</TableHead>
            <TableHead>Share of cost</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {nodes.map((node) => (
            <TableRow key={node.node}>
              <TableCell className="font-mono text-xs">{formatStep(node.node)}</TableCell>
              <TableCell className="text-right tabular-nums">{node.attempts}</TableCell>
              <TableCell className="text-right tabular-nums">{formatDuration(node.durationMs)}</TableCell>
              <TableCell className="text-right tabular-nums">{node.modelCalls}</TableCell>
              <TableCell className="text-right tabular-nums">
                {formatTokens(node.tokens.input)} / {formatTokens(node.tokens.output)}
              </TableCell>
              <TableCell className="text-right tabular-nums">{formatCostSplit(node.cost)}</TableCell>
              <TableCell>
                <ShareBar part={node.durationMs} whole={totalMs} label="the time" />
              </TableCell>
              <TableCell>
                <ShareBar part={node.cost.total} whole={totalCost} label="the cost" />
              </TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </div>
  );
}
