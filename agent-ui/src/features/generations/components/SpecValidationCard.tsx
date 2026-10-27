"use client";

import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Spinner } from "@/components/ui/spinner";
import { IssueList } from "@/features/specs/components/IssueList";
import type { TEditorIssue, TSpecValidation } from "@/features/specs/hooks/use-spec-validation";

type SpecValidationCardProps = {
  title: string;
  validation: TSpecValidation;
  emptyText: string;
  onSelect: (issue: TEditorIssue) => void;
};

export function SpecValidationCard({ title, validation, emptyText, onSelect }: SpecValidationCardProps) {
  return (
    <Card size="sm">
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          {title}
          {validation.isChecking && <Spinner />}
          {validation.errorCount > 0 && <Badge variant="destructive">{validation.errorCount} errors</Badge>}
          {validation.warningCount > 0 && <Badge variant="outline">{validation.warningCount} warnings</Badge>}
        </CardTitle>
      </CardHeader>
      <CardContent>
        <IssueList
          issues={validation.issues}
          isChecking={validation.isChecking}
          isEmpty={validation.isEmpty}
          onSelect={onSelect}
          emptyText={emptyText}
        />
        {validation.requestError && <p className="mt-2 text-sm text-destructive">{validation.requestError.message}</p>}
      </CardContent>
    </Card>
  );
}
