import { Card, CardContent } from "@/components/ui/card";
import { formatCostSplit, formatTokens, formatUsd } from "@/lib/format-usage";
import { formatDuration } from "@/features/generations/lib/status";
import type { TUsageReport } from "../types";

type UsageTilesProps = {
  totals: TUsageReport["totals"];
};

type TileProps = {
  label: string;
  value: string;
  detail?: string;
};

function Tile({ label, value, detail }: TileProps) {
  return (
    <Card size="sm" className="min-w-0">
      <CardContent className="flex flex-col gap-0.5">
        <span className="text-xs text-muted-foreground">{label}</span>
        <span className="truncate text-xl font-semibold tabular-nums">{value}</span>
        {detail && <span className="truncate text-xs text-muted-foreground">{detail}</span>}
      </CardContent>
    </Card>
  );
}

export function UsageTiles({ totals }: UsageTilesProps) {
  return (
    <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
      <Tile
        label="Generations"
        value={String(totals.generations)}
        detail={`${totals.completed} completed · ${totals.failed} failed`}
      />
      <Tile
        label="Success rate"
        value={totals.successRate == null ? "—" : `${Math.round(totals.successRate * 100)}%`}
        detail="of finished runs"
      />
      <Tile
        label="Total wall time"
        value={formatDuration(totals.wallMs)}
        detail={`engine ${formatDuration(totals.engineMs)} · sandbox ${formatDuration(totals.sandboxMs)}`}
      />
      <Tile
        label="Model calls"
        value={formatTokens(totals.modelCalls)}
        detail={`${formatTokens(totals.tokens.input)} in / ${formatTokens(totals.tokens.output)} out tokens`}
      />
      <Tile
        label="Cost"
        value={formatCostSplit(totals.cost)}
        detail={totals.cost.unpriced ? `${totals.cost.unpriced} call(s) without a price` : "reported + estimated"}
      />
      <Tile
        label="Avg cost / completed"
        value={totals.avgCostPerCompleted == null ? "—" : formatUsd(totals.avgCostPerCompleted)}
      />
      <Tile
        label="Avg duration / completed"
        value={totals.avgWallMsPerCompleted == null ? "—" : formatDuration(totals.avgWallMsPerCompleted)}
      />
      <Tile label="Cache reads" value={formatTokens(totals.tokens.cacheRead)} detail="input tokens served from cache" />
    </div>
  );
}
