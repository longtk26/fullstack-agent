import { ExternalLink } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { formatCostSplit, formatTokens } from "@/lib/format-usage";
import type { TUsageRollup } from "@/types/usage";
import { formatDuration } from "../../lib/status";

type TraceSummaryProps = {
  usage: TUsageRollup;
  langsmithUrl: string | null;
};

type StatProps = {
  label: string;
  value: string;
  detail?: string;
};

function Stat({ label, value, detail }: StatProps) {
  return (
    <Card size="sm" className="min-w-0">
      <CardContent className="flex flex-col gap-0.5">
        <span className="text-xs text-muted-foreground">{label}</span>
        <span className="truncate text-lg font-semibold tabular-nums">{value}</span>
        {detail && <span className="truncate text-xs text-muted-foreground">{detail}</span>}
      </CardContent>
    </Card>
  );
}

/** Totals of the run: time, engine vs sandbox time, model calls, tokens and cost (estimated cost labelled). */
export function TraceSummary({ usage, langsmithUrl }: TraceSummaryProps) {
  const { tokens, cost } = usage;
  return (
    <div className="flex flex-col gap-3">
      <div className="grid grid-cols-2 gap-3 md:grid-cols-3 xl:grid-cols-5">
        <Stat label="Wall time" value={formatDuration(usage.wallMs)} />
        <Stat
          label="Engine / sandbox time"
          value={`${formatDuration(usage.engineMs)} / ${formatDuration(usage.sandboxMs)}`}
        />
        <Stat label="Model calls" value={String(usage.modelCalls)} detail={`${usage.engineCalls} engine run(s)`} />
        <Stat
          label="Tokens in / out"
          value={`${formatTokens(tokens.input)} / ${formatTokens(tokens.output)}`}
          detail={`cache read ${formatTokens(tokens.cacheRead)} · write ${formatTokens(tokens.cacheWrite)}`}
        />
        <Stat
          label="Cost"
          value={formatCostSplit(cost)}
          detail={cost.unpriced ? `${cost.unpriced} call(s) without a price` : undefined}
        />
      </div>
      {langsmithUrl && (
        <div>
          <Button variant="outline" size="sm" render={<a href={langsmithUrl} target="_blank" rel="noreferrer" />} nativeButton={false}>
            <ExternalLink /> Open in LangSmith
          </Button>
        </div>
      )}
    </div>
  );
}
