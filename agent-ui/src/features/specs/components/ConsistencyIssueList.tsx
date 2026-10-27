"use client";

import { CircleAlert, CircleCheck, TriangleAlert } from "lucide-react";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Spinner } from "@/components/ui/spinner";
import { cn } from "@/lib/utils";
import { SPEC_KINDS } from "../lib/spec-kinds";
import type { TSpecIssue, TSpecKind } from "../types";

type ConsistencyIssueListProps = {
  issues: TSpecIssue[];
  isReady: boolean;
  isChecking: boolean;
  /** Jumps to `pointer` in the FrontendSpec or BackendSpec editor. */
  onSelect: (kind: TSpecKind, pointer: string) => void;
};

function Location({ kind, pointer, onSelect }: { kind: TSpecKind; pointer: string; onSelect: ConsistencyIssueListProps["onSelect"] }) {
  return (
    <button
      type="button"
      onClick={() => onSelect(kind, pointer)}
      className="block max-w-full truncate rounded-sm text-left font-mono text-xs text-muted-foreground underline-offset-2 hover:text-foreground hover:underline"
    >
      {SPEC_KINDS[kind].label} · {pointer || "/"}
    </button>
  );
}

/** Frontend ↔ contract mismatches; each names the place to change in the FrontendSpec and, if known, the BackendSpec. */
export function ConsistencyIssueList({ issues, isReady, isChecking, onSelect }: ConsistencyIssueListProps) {
  if (!isReady) {
    return <p className="text-sm text-muted-foreground">Checked once both specs are valid.</p>;
  }
  if (issues.length === 0) {
    return (
      <p className="flex items-center gap-2 text-sm text-muted-foreground">
        {isChecking ? <Spinner /> : <CircleCheck className="size-4 text-success" />}
        {isChecking ? "Checking the pair…" : "The FrontendSpec only uses what the BackendSpec provides."}
      </p>
    );
  }
  return (
    <ScrollArea className="max-h-64">
      <ul className="flex flex-col gap-2 pr-3">
        {issues.map((issue, index) => {
          const Icon = issue.severity === "error" ? CircleAlert : TriangleAlert;
          return (
            <li key={`${issue.code}-${issue.path}-${index}`} className="flex gap-2 px-2 text-sm">
              <Icon
                className={cn(
                  "mt-0.5 size-4 shrink-0",
                  issue.severity === "error" ? "text-destructive" : "text-warning-foreground dark:text-warning",
                )}
              />
              <span className="min-w-0">
                <span className="block">{issue.message}</span>
                <span className="block font-mono text-xs text-muted-foreground">{issue.code}</span>
                <Location kind="frontend" pointer={issue.path} onSelect={onSelect} />
                {issue.backendPath != null && <Location kind="backend" pointer={issue.backendPath} onSelect={onSelect} />}
                {issue.hint && <span className="block text-xs text-muted-foreground">{issue.hint}</span>}
              </span>
            </li>
          );
        })}
      </ul>
    </ScrollArea>
  );
}
