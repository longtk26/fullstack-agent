import { ArrowRight, CircleCheck, CircleX, TriangleAlert } from "lucide-react";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Checkbox } from "@/components/ui/checkbox";
import { Label } from "@/components/ui/label";
import { Stack } from "@/components/layout/Stack";
import { formatTokens, formatUsd } from "@/lib/format-usage";
import { summarizeFrontendSpec } from "../lib/frontend-spec-summary";
import { summarizeSpec } from "../lib/spec-summary";
import type { TSpecDraft, TValidationReport } from "../types";
import { NotesPanel } from "./NotesPanel";

const REPORT_LABELS = { backend: "BackendSpec", frontend: "FrontendSpec", pair: "Consistency" } as const;

type DraftResultProps = {
  draft: TSpecDraft;
  needsAcknowledgement: boolean;
  acknowledged: boolean;
  onAcknowledge: (value: boolean) => void;
  onOpen: () => void;
  onDiscard: () => void;
};

function usageLine(draft: TSpecDraft): string {
  const { usage } = draft;
  const seconds = Math.round((usage.engineMs ?? 0) / 1000);
  const tokens = (usage.inputTokens ?? 0) + (usage.outputTokens ?? 0);
  const cost = usage.unpriced ? "cost unknown" : formatUsd(usage.costUsd ?? 0);
  const images = usage.images;
  const imagePart = images ? ` · ${images.count} photos (${formatUsd(images.costUsd)})` : "";
  return `${draft.engine} · ${usage.modelCalls ?? 0} model calls · ${formatTokens(tokens)} tokens · ${cost}${imagePart} · ${seconds} s`;
}

function ReportBadge({ name, report }: { name: keyof typeof REPORT_LABELS; report: TValidationReport }) {
  const count = report.errors.length;
  return (
    <Badge variant={count ? "destructive" : "outline"}>
      {count ? <CircleX /> : <CircleCheck />}
      {REPORT_LABELS[name]}: {count ? `${count} errors` : "valid"}
    </Badge>
  );
}

export function DraftResult({ draft, needsAcknowledgement, acknowledged, onAcknowledge, onOpen, onDiscard }: DraftResultProps) {
  if (draft.status === "FAILED") {
    return (
      <Alert variant="destructive">
        <CircleX />
        <AlertTitle>The draft failed</AlertTitle>
        <AlertDescription>
          <Stack gap="xs">
            <span>{draft.error ?? "Unknown error"}</span>
            <div>
              <Button size="sm" variant="outline" onClick={onDiscard}>
                Dismiss
              </Button>
            </div>
          </Stack>
        </AlertDescription>
      </Alert>
    );
  }

  const backend = summarizeSpec(draft.backendSpec);
  const frontend = summarizeFrontendSpec(draft.frontendSpec);
  const reports = (Object.keys(REPORT_LABELS) as (keyof typeof REPORT_LABELS)[]).flatMap((name) => {
    const report = draft.validation[name];
    return report ? [{ name, report }] : [];
  });
  const canOpen = !needsAcknowledgement || acknowledged;

  return (
    <Stack gap="md">
      <Card size="sm">
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            {draft.status === "SUCCEEDED" ? "Draft ready" : "Draft needs fixes"}
            {(frontend.projectName ?? backend.projectName) && (
              <span className="font-normal text-muted-foreground">· {frontend.projectName ?? backend.projectName}</span>
            )}
          </CardTitle>
          <CardDescription>{usageLine(draft)}</CardDescription>
        </CardHeader>
        <CardContent>
          <Stack gap="sm">
            <Stack direction="row" gap="xs" wrap>
              {reports.map(({ name, report }) => (
                <ReportBadge key={name} name={name} report={report} />
              ))}
              {draft.attempts > 0 && <Badge variant="secondary">{draft.attempts} repair passes</Badge>}
            </Stack>
            {draft.frontendSpec && (
              <p className="text-sm">
                {frontend.pages.length} pages:{" "}
                <span className="font-mono text-xs text-muted-foreground">
                  {frontend.pages.map((page) => page.route).join("  ")}
                </span>
              </p>
            )}
            {draft.backendSpec && (
              <p className="text-sm">
                {backend.entities.length} entities ({backend.entities.map((entity) => entity.name).join(", ")}),{" "}
                {backend.operations.length} operations
              </p>
            )}
          </Stack>
        </CardContent>
      </Card>

      {draft.status === "NEEDS_REVIEW" && (
        <Alert>
          <TriangleAlert />
          <AlertTitle>Still invalid after {draft.attempts} repair passes</AlertTitle>
          <AlertDescription>
            Open the draft in the editor: the remaining errors are marked there. {draft.error}
          </AlertDescription>
        </Alert>
      )}

      <NotesPanel kind="unresolved" notes={draft.unresolved} />
      <NotesPanel kind="assumptions" notes={draft.assumptions} />

      <Stack direction="row" justify="between" align="center" wrap className="gap-y-3">
        {needsAcknowledgement ? (
          <Label className="flex items-center gap-2 font-normal">
            <Checkbox checked={acknowledged} onCheckedChange={(value) => onAcknowledge(value === true)} />
            I reviewed the assumptions and unresolved items
          </Label>
        ) : (
          <span />
        )}
        <Stack direction="row" gap="xs">
          <Button variant="ghost" onClick={onDiscard}>
            Discard
          </Button>
          <Button onClick={onOpen} disabled={!canOpen}>
            Open in editor <ArrowRight />
          </Button>
        </Stack>
      </Stack>
      <p className="text-xs text-muted-foreground">
        Opening replaces what the editor{draft.mode === "dynamic" ? "s" : ""} currently hold. The draft is not
        submitted: review it there, then generate.
      </p>
    </Stack>
  );
}
