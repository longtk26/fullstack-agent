"use client";

import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import type { TCheckItem, TValidationHistory } from "../../types";

const VARIANT: Record<string, "secondary" | "destructive" | "outline"> = {
  passed: "secondary",
  failed: "destructive",
  skipped: "outline",
};

type JourneyResultsProps = {
  history: TValidationHistory | undefined;
  loading?: boolean;
};

type TStepComparison = {
  step: number;
  do: string;
  mockItem?: TCheckItem;
  liveItem?: TCheckItem;
};

type TJourneyGroup = {
  id: string;
  title: string;
  steps: TStepComparison[];
};

export function JourneyResults({ history, loading }: JourneyResultsProps) {
  if (loading) return <Skeleton className="h-48 w-full" />;
  if (!history || history.checks.length === 0) return null;

  const mockCheck = history.checks.find((c) => c.check === "frontend:journeys");
  const liveCheck = history.checks.find((c) => c.check === "integration:journeys");

  const mockRun = mockCheck?.runs[mockCheck.runs.length - 1];
  const liveRun = liveCheck?.runs[liveCheck.runs.length - 1];

  const mockItems: TCheckItem[] = mockRun?.items || [];
  const liveItems: TCheckItem[] = liveRun?.items || [];

  if (mockItems.length === 0 && liveItems.length === 0) {
    return null;
  }

  // Group steps by journey
  const journeysMap = new Map<string, TJourneyGroup>();

  const processItem = (item: TCheckItem, isLive: boolean) => {
    if (!item.journey) return;
    let group = journeysMap.get(item.journey);
    if (!group) {
      group = {
        id: item.journey,
        title: item.journeyTitle || item.journey,
        steps: [],
      };
      journeysMap.set(item.journey, group);
    }
    const stepIdx = item.step ?? 0;
    let stepComp = group.steps.find((s) => s.step === stepIdx);
    if (!stepComp) {
      stepComp = { step: stepIdx, do: item.do || "step" };
      group.steps.push(stepComp);
    }
    if (isLive) {
      stepComp.liveItem = item;
    } else {
      stepComp.mockItem = item;
    }
  };

  mockItems.forEach((item) => processItem(item, false));
  liveItems.forEach((item) => processItem(item, true));

  const journeys = Array.from(journeysMap.values());
  for (const j of journeys) {
    j.steps.sort((a, b) => a.step - b.step);
  }

  return (
    <div className="flex flex-col gap-4">
      {journeys.map((journey) => (
        <div key={journey.id} className="rounded-lg border bg-card text-card-foreground">
          <div className="border-b px-4 py-3">
            <h4 className="text-sm font-semibold tracking-tight">
              {journey.title} <span className="font-mono text-xs font-normal text-muted-foreground">({journey.id})</span>
            </h4>
          </div>
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead className="w-16">Step</TableHead>
                <TableHead>Action</TableHead>
                <TableHead className="w-32">Mock API</TableHead>
                <TableHead className="w-32">Live API</TableHead>
                <TableHead>Details</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {journey.steps.map(({ step, do: stepDo, mockItem, liveItem }) => {
                const mockStatus = mockItem?.status || (mockRun ? "not_run" : "—");
                const liveStatus = liveItem?.status || (liveRun ? "not_run" : "—");
                const errorMsg = liveItem?.message || mockItem?.message;
                return (
                  <TableRow key={step}>
                    <TableCell className="font-mono text-xs">{step}</TableCell>
                    <TableCell className="font-medium text-xs">{stepDo}</TableCell>
                    <TableCell>
                      {mockStatus !== "—" ? (
                        <Badge variant={VARIANT[mockStatus] ?? "outline"}>{mockStatus}</Badge>
                      ) : (
                        <span className="text-xs text-muted-foreground">—</span>
                      )}
                    </TableCell>
                    <TableCell>
                      {liveStatus !== "—" ? (
                        <Badge variant={VARIANT[liveStatus] ?? "outline"}>{liveStatus}</Badge>
                      ) : (
                        <span className="text-xs text-muted-foreground">—</span>
                      )}
                    </TableCell>
                    <TableCell className="text-xs text-muted-foreground">
                      {errorMsg ? <span className="text-destructive">{errorMsg}</span> : "—"}
                    </TableCell>
                  </TableRow>
                );
              })}
            </TableBody>
          </Table>
        </div>
      ))}
    </div>
  );
}
