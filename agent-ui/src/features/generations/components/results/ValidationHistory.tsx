"use client";

import { Fragment, useState } from "react";
import { ChevronRight } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { cn } from "@/lib/utils";
import { formatDuration } from "../../lib/status";
import type { TCheckItem, TCheckRun, TCheckStatus, TValidationHistory } from "../../types";

const VARIANT: Record<TCheckStatus, "secondary" | "destructive" | "outline"> = {
  passed: "secondary",
  failed: "destructive",
  skipped: "outline",
  not_run: "outline",
};

type ValidationHistoryProps = {
  history: TValidationHistory | undefined;
  loading: boolean;
};

export function ValidationHistory({ history, loading }: ValidationHistoryProps) {
  const [open, setOpen] = useState<string | null>(null);
  if (loading) return <Skeleton className="h-64 w-full" />;
  if (!history || history.checks.length === 0) {
    return <p className="text-sm text-muted-foreground">No validation has run yet.</p>;
  }
  return (
    <div className="rounded-lg border">
      <Table>
        <TableHeader>
          <TableRow>
            <TableHead className="w-8" />
            <TableHead>Check</TableHead>
            <TableHead>Result</TableHead>
            <TableHead>History</TableHead>
            <TableHead className="text-right">Duration</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {history.checks.map(({ check, runs }) => {
            const latest = runs[runs.length - 1];
            const expanded = open === check;
            return (
              <Fragment key={check}>
                <TableRow className="cursor-pointer" onClick={() => setOpen(expanded ? null : check)}>
                  <TableCell>
                    <Button variant="ghost" size="icon-xs" aria-label={expanded ? "Collapse" : "Expand"}>
                      <ChevronRight className={cn("transition-transform", expanded && "rotate-90")} />
                    </Button>
                  </TableCell>
                  <TableCell className="font-mono text-xs">{check}</TableCell>
                  <TableCell>
                    <Badge variant={VARIANT[latest.status] ?? "outline"}>{latest.status.replaceAll("_", " ")}</Badge>
                  </TableCell>
                  <TableCell className="text-xs text-muted-foreground">{historyLabel(runs)}</TableCell>
                  <TableCell className="text-right text-xs tabular-nums">
                    {latest.durationMs != null ? formatDuration(latest.durationMs) : "—"}
                  </TableCell>
                </TableRow>
                {expanded && (
                  <TableRow>
                    <TableCell />
                    <TableCell colSpan={4} className="whitespace-normal">
                      <CheckRunDetails runs={runs} />
                    </TableCell>
                  </TableRow>
                )}
              </Fragment>
            );
          })}
        </TableBody>
      </Table>
    </div>
  );
}

/** e.g. "failed → passed (repair #1)": attempt n+1 runs after repair n. */
function historyLabel(runs: TCheckRun[]): string {
  if (runs.length < 2) return "—";
  const path = runs.map((run) => run.status.replaceAll("_", " ")).join(" → ");
  return `${path} (${runs.length - 1} repair${runs.length > 2 ? "s" : ""})`;
}

function CheckRunDetails({ runs }: { runs: TCheckRun[] }) {
  return (
    <div className="flex flex-col gap-3 py-1">
      {runs.map((run) => (
        <div key={run.attempt} className="flex flex-col gap-1.5">
          <p className="text-xs font-medium">
            Attempt {run.attempt}
            {run.attempt > 1 && <span className="text-muted-foreground"> · after repair #{run.attempt - 1}</span>}
            <span className="font-normal text-muted-foreground"> — {run.summary ?? run.status}</span>
          </p>
          {run.items.length > 0 && (
            <ul className="flex flex-col gap-1 text-xs">
              {run.items.slice(0, 25).map((item, index) => (
                <li key={index} className="rounded-md bg-muted/60 px-2 py-1">
                  <CheckItem item={item} />
                </li>
              ))}
            </ul>
          )}
          {run.output && run.status === "failed" && (
            <pre className="max-h-64 overflow-auto rounded-md bg-muted/60 p-2 text-xs">{run.output}</pre>
          )}
        </div>
      ))}
    </div>
  );
}

function CheckItem({ item }: { item: TCheckItem }) {
  const where = item.file ?? item.table ?? item.operation ?? item.test ?? "";
  return (
    <span className="flex flex-col gap-0.5">
      <span>
        <span className="font-mono">{item.line ? `${where}:${item.line}` : where}</span>
        {(item.code ?? item.rule) && <Badge variant="outline" className="mx-1.5">{item.code ?? item.rule}</Badge>}
        {item.message}
      </span>
      {item.hint && <span className="text-muted-foreground">Skill rule: {item.hint}</span>}
    </span>
  );
}
