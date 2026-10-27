"use client";

import { useRouter } from "next/navigation";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { useNow } from "@/hooks/use-now";
import { elapsedMs, formatDuration, formatStep, isTerminal } from "../lib/status";
import type { TGeneration } from "../types";
import { ModeLaneBadges } from "./ModeLaneBadges";
import { StatusBadge } from "./StatusBadge";

type GenerationsTableProps = {
  items: TGeneration[];
};

const dateFormat = new Intl.DateTimeFormat(undefined, { dateStyle: "medium", timeStyle: "short" });

export function GenerationsTable({ items }: GenerationsTableProps) {
  const router = useRouter();
  const now = useNow(items.some((item) => !isTerminal(item.status)));

  return (
    <Table>
      <TableHeader>
        <TableRow>
          <TableHead>ID</TableHead>
          <TableHead>Project</TableHead>
          <TableHead>Mode</TableHead>
          <TableHead>Engine</TableHead>
          <TableHead>Status</TableHead>
          <TableHead>Current step</TableHead>
          <TableHead className="text-right">Duration</TableHead>
          <TableHead className="text-right">Created</TableHead>
        </TableRow>
      </TableHeader>
      <TableBody>
        {items.map((item) => {
          const duration = elapsedMs(item.startedAt, item.finishedAt, now);
          const href = `/generations/${item.generationId}`;
          return (
            <TableRow
              key={item.generationId}
              className="cursor-pointer"
              tabIndex={0}
              onClick={() => router.push(href)}
              onKeyDown={(event) => event.key === "Enter" && router.push(href)}
            >
              <TableCell className="font-mono text-xs">{item.generationId}</TableCell>
              <TableCell className="font-medium">{item.projectName ?? "—"}</TableCell>
              <TableCell>
                <ModeLaneBadges mode={item.mode} lanes={item.lanes} compact />
              </TableCell>
              <TableCell className="text-muted-foreground">{item.engine}</TableCell>
              <TableCell>
                <StatusBadge status={item.status} />
              </TableCell>
              <TableCell className="text-muted-foreground">
                {isTerminal(item.status) ? "—" : formatStep(item.currentStep)}
              </TableCell>
              <TableCell className="text-right tabular-nums">
                {duration === null ? "—" : formatDuration(duration)}
              </TableCell>
              <TableCell className="text-right text-muted-foreground">
                {item.createdAt ? dateFormat.format(new Date(item.createdAt)) : "—"}
              </TableCell>
            </TableRow>
          );
        })}
      </TableBody>
    </Table>
  );
}
