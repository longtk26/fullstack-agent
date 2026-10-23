"use client";

import { useMemo } from "react";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Sheet, SheetContent, SheetDescription, SheetHeader, SheetTitle } from "@/components/ui/sheet";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Stack } from "@/components/layout/Stack";
import { formatDuration, formatStep } from "../../lib/status";
import type { TGenerationEvent, TStepRun } from "../../types";
import { EventRow } from "./EventRow";

const MAX_NODE_EVENTS = 300;

type StepDrawerProps = {
  node: string | null;
  steps: TStepRun[];
  events: TGenerationEvent[];
  onClose: () => void;
};

const timeFormat = new Intl.DateTimeFormat(undefined, { timeStyle: "medium" });

function runDuration(run: TStepRun): string {
  if (!run.startedAt || !run.finishedAt) return run.status === "running" ? "running" : "—";
  return formatDuration(Date.parse(run.finishedAt) - Date.parse(run.startedAt));
}

export function StepDrawer({ node, steps, events, onClose }: StepDrawerProps) {
  const runs = useMemo(() => steps.filter((step) => step.node === node), [steps, node]);
  const nodeEvents = useMemo(
    () => events.filter((event) => event.step === node).slice(-MAX_NODE_EVENTS),
    [events, node],
  );

  return (
    <Sheet open={node !== null} onOpenChange={(open) => !open && onClose()}>
      <SheetContent side="right" className="gap-0 data-[side=right]:w-full data-[side=right]:sm:max-w-2xl">
        <SheetHeader>
          <SheetTitle className="capitalize">{formatStep(node)}</SheetTitle>
          <SheetDescription>
            {runs.length === 0 ? "This step has not run yet." : `${runs.length} run${runs.length > 1 ? "s" : ""}`}
          </SheetDescription>
        </SheetHeader>
        <div className="flex-1 overflow-y-auto px-4 pb-6">
          <Stack gap="md">
            {runs.map((run) => (
              <Card key={run.id} size="sm">
                <CardHeader>
                  <CardTitle className="flex flex-wrap items-center gap-2 text-sm">
                    Attempt {run.attempt}
                    <Badge variant={run.status === "failed" ? "destructive" : "secondary"}>{run.status}</Badge>
                    <span className="text-xs font-normal text-muted-foreground">
                      {run.startedAt ? timeFormat.format(new Date(run.startedAt)) : "—"} · {runDuration(run)}
                    </span>
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  <Stack gap="sm">
                    {Object.keys(run.summary).length > 0 && (
                      <pre className="max-h-48 overflow-auto rounded-md bg-muted p-2 text-xs">
                        {JSON.stringify(run.summary, null, 2)}
                      </pre>
                    )}
                    {run.invocations.length > 0 ? (
                      <div className="overflow-x-auto rounded-md border">
                        <Table>
                          <TableHeader>
                            <TableRow>
                              <TableHead>Purpose</TableHead>
                              <TableHead>Status</TableHead>
                              <TableHead className="text-right">Turns</TableHead>
                              <TableHead className="text-right">Tokens in / out</TableHead>
                              <TableHead className="text-right">Time</TableHead>
                              <TableHead className="text-right">Exit</TableHead>
                            </TableRow>
                          </TableHeader>
                          <TableBody>
                            {run.invocations.map((invocation) => (
                              <TableRow key={invocation.id}>
                                <TableCell className="text-xs">{invocation.purpose}</TableCell>
                                <TableCell className="text-xs">{invocation.status}</TableCell>
                                <TableCell className="text-right text-xs tabular-nums">{invocation.turns ?? "—"}</TableCell>
                                <TableCell className="text-right text-xs tabular-nums">
                                  {invocation.inputTokens ?? "—"} / {invocation.outputTokens ?? "—"}
                                </TableCell>
                                <TableCell className="text-right text-xs tabular-nums">
                                  {invocation.durationMs !== null ? formatDuration(invocation.durationMs) : "—"}
                                </TableCell>
                                <TableCell className="text-right text-xs tabular-nums">
                                  {invocation.exitCode ?? "—"}
                                </TableCell>
                              </TableRow>
                            ))}
                          </TableBody>
                        </Table>
                      </div>
                    ) : (
                      <p className="text-xs text-muted-foreground">No engine invocations.</p>
                    )}
                  </Stack>
                </CardContent>
              </Card>
            ))}
            <Stack gap="xs">
              <h3 className="text-sm font-medium">Events ({nodeEvents.length})</h3>
              <div className="rounded-lg border">
                {nodeEvents.map((event) => (
                  <EventRow key={event.id} event={event} showStep={false} />
                ))}
                {nodeEvents.length === 0 && <p className="p-3 text-xs text-muted-foreground">No events yet.</p>}
              </div>
            </Stack>
          </Stack>
        </div>
      </SheetContent>
    </Sheet>
  );
}
