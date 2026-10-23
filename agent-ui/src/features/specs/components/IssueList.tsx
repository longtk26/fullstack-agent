"use client";

import { CircleAlert, CircleCheck, TriangleAlert } from "lucide-react";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Spinner } from "@/components/ui/spinner";
import { cn } from "@/lib/utils";
import type { TEditorIssue } from "../hooks/use-spec-validation";

type IssueListProps = {
  issues: TEditorIssue[];
  isChecking: boolean;
  isEmpty: boolean;
  onSelect: (issue: TEditorIssue) => void;
};

export function IssueList({ issues, isChecking, isEmpty, onSelect }: IssueListProps) {
  if (isEmpty) {
    return <p className="text-sm text-muted-foreground">Paste, load or import a BackendSpec to validate it.</p>;
  }
  if (issues.length === 0) {
    return (
      <p className="flex items-center gap-2 text-sm text-muted-foreground">
        {isChecking ? <Spinner /> : <CircleCheck className="size-4 text-success" />}
        {isChecking ? "Validating…" : "No issues: the spec is valid."}
      </p>
    );
  }
  return (
    <ScrollArea className="max-h-64">
      <ul className="flex flex-col gap-1 pr-3">
        {issues.map((issue, index) => {
          const Icon = issue.severity === "error" ? CircleAlert : TriangleAlert;
          return (
            <li key={`${issue.code}-${issue.path}-${index}`}>
              <button
                type="button"
                onClick={() => onSelect(issue)}
                className="flex w-full gap-2 rounded-md px-2 py-1.5 text-left text-sm transition-colors hover:bg-muted"
              >
                <Icon
                  className={cn(
                    "mt-0.5 size-4 shrink-0",
                    issue.severity === "error" ? "text-destructive" : "text-warning-foreground dark:text-warning",
                  )}
                />
                <span className="min-w-0">
                  <span className="block">{issue.message}</span>
                  <span className="block truncate font-mono text-xs text-muted-foreground">
                    {issue.code}
                    {issue.path && ` · ${issue.path}`}
                  </span>
                  {issue.hint && <span className="block text-xs text-muted-foreground">{issue.hint}</span>}
                </span>
              </button>
            </li>
          );
        })}
      </ul>
    </ScrollArea>
  );
}
