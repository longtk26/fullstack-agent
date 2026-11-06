"use client";

import { useMemo } from "react";
import Link from "next/link";
import {
  AlertTriangle,
  Ban,
  CheckCircle2,
  FileCode2,
  Image as ImageIcon,
  Loader2,
  Sparkles,
} from "lucide-react";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from "@/components/ui/card";
import { Stack } from "@/components/layout/Stack";
import { useSpecDraft } from "@/features/specs/hooks/use-spec-queries";
import { useCancelGeneration } from "../../hooks/use-generation-mutations";
import type { TGenerationDetail, TGenerationEvent } from "../../types";

type SpecPhaseCardProps = {
  detail: TGenerationDetail;
  events: TGenerationEvent[];
};

export function SpecPhaseCard({ detail, events }: SpecPhaseCardProps) {
  const draftId = detail.options?.draftId ?? null;
  const draftQuery = useSpecDraft(draftId);
  const draft = draftQuery.data;
  const cancel = useCancelGeneration(detail.generationId);

  // Derive latest progress from events or draft query
  const lastDraftProgressEvent = useMemo(
    () => events.findLast((e) => e.type === "draft.progress"),
    [events],
  );
  const progressText =
    (lastDraftProgressEvent?.payload?.progress as string | undefined) ??
    draft?.progress ??
    (detail.status === "DRAFTING" ? "Drafting requirements…" : "Spec ready");

  // If this generation had no draft associated, don't show the spec phase card
  if (!draftId && detail.status !== "DRAFTING" && detail.status !== "NEEDS_REVIEW") {
    return null;
  }

  // 1. DRAFTING STATE
  if (detail.status === "DRAFTING") {
    return (
      <Card className="border-info/30 bg-info/5 shadow-xs">
        <CardHeader className="py-3">
          <div className="flex items-center justify-between">
            <CardTitle className="flex items-center gap-2 text-base">
              <Loader2 className="size-4 animate-spin text-info" />
              Spec Drafting Phase
            </CardTitle>
            <Badge variant="outline" className="border-info/40 bg-info/10 text-info">
              Drafting in progress
            </Badge>
          </div>
          <CardDescription className="text-sm">
            {progressText} · The requirements are being drafted and validated before generation starts.
          </CardDescription>
        </CardHeader>
        <CardFooter className="flex justify-end gap-2 py-2">
          <Button
            variant="outline"
            size="sm"
            onClick={() => cancel.mutate()}
            disabled={cancel.isPending}
            className="text-muted-foreground hover:text-destructive"
          >
            <Ban className="size-3.5" />
            Cancel drafting
          </Button>
        </CardFooter>
      </Card>
    );
  }

  // 2. NEEDS_REVIEW STATE
  if (detail.status === "NEEDS_REVIEW") {
    const errors =
      (events.findLast((e) => e.type === "status.changed" && e.status === "NEEDS_REVIEW")?.payload
        ?.errors as Array<{ message?: string; file?: string }> | undefined) ??
      [
        ...(draft?.validation?.backend?.errors ?? []),
        ...(draft?.validation?.frontend?.errors ?? []),
        ...(draft?.validation?.pair?.errors ?? []),
      ];

    return (
      <Card className="border-warning/40 bg-warning/5 shadow-xs">
        <CardHeader className="py-3">
          <div className="flex items-center justify-between">
            <CardTitle className="flex items-center gap-2 text-base text-warning-foreground dark:text-warning">
              <AlertTriangle className="size-4 text-warning" />
              Draft Needs Review
            </CardTitle>
            <div className="flex items-center gap-2">
              <Badge variant="secondary" className="bg-warning/20 text-warning-foreground dark:text-warning">
                Needs review
              </Badge>
            </div>
          </div>
          <CardDescription>
            The spec draft still has validation issues after its automatic repairs. Open the draft to fix them, or
            cancel and draft the requirement again.
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4 py-2">
          {errors.length > 0 && (
            <Alert variant="destructive" className="py-2">
              <AlertTitle className="text-xs font-semibold">Validation issues ({errors.length})</AlertTitle>
              <AlertDescription className="mt-1 space-y-1 text-xs">
                {errors.slice(0, 5).map((err, i) => {
                  const location = ("file" in err && err.file) || ("path" in err && err.path) || null;
                  return (
                    <div key={i}>
                      {location && <span className="font-mono font-semibold">{String(location)}: </span>}
                      {err.message || JSON.stringify(err)}
                    </div>
                  );
                })}
                {errors.length > 5 && <div className="text-muted-foreground">+{errors.length - 5} more issues</div>}
              </AlertDescription>
            </Alert>
          )}

        </CardContent>
        <CardFooter className="flex justify-between gap-2 py-3">
          <Button
            variant="outline"
            size="sm"
            onClick={() => cancel.mutate()}
            disabled={cancel.isPending}
            className="text-muted-foreground hover:text-destructive"
          >
            <Ban className="size-3.5" />
            Cancel
          </Button>
          {draftId && (
            <Button
              size="sm"
              render={<Link href={`/generations/new?mode=${detail.mode}&draftId=${draftId}`} />}
              nativeButton={false}
            >
              <FileCode2 className="size-3.5" />
              Open the draft
            </Button>
          )}
        </CardFooter>
      </Card>
    );
  }

  // 3. COMPLETED / IN-PROGRESS SPEC PHASE SUMMARY (Read-only)
  const pagesCount = Array.isArray(draft?.frontendSpec?.pages) ? draft.frontendSpec.pages.length : null;
  const entitiesCount = Array.isArray(draft?.backendSpec?.entities) ? draft.backendSpec.entities.length : null;
  const photosCount = Array.isArray(draft?.frontendSpec?.assets)
    ? draft.frontendSpec.assets.filter((a: { source?: string }) => a?.source === "photo" || a?.source?.startsWith("upload:")).length
    : null;
  const assumptionsCount = draft?.assumptions?.length ?? 0;

  return (
    <Card className="border bg-card/60 shadow-xs">
      <CardHeader className="py-3">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <CheckCircle2 className="size-4 text-success" />
            <span className="text-sm font-semibold">Spec Phase</span>
            <Badge variant="outline" className="border-success/30 bg-success/10 text-success text-xs">
              Drafted
            </Badge>
          </div>
          {draftId && (
            <Link
              href={`/generations/new?mode=${detail.mode}&draftId=${draftId}`}
              className="text-xs text-muted-foreground hover:text-foreground flex items-center gap-1"
            >
              <FileCode2 className="size-3.5" />
              View full draft
            </Link>
          )}
        </div>
      </CardHeader>
      <CardContent className="py-1">
        <Stack direction="row" gap="sm" wrap align="center" className="text-xs text-muted-foreground">
          {pagesCount !== null && (
            <Badge variant="secondary" className="gap-1 font-normal">
              <FileCode2 className="size-3" />
              {pagesCount} pages
            </Badge>
          )}
          {entitiesCount !== null && (
            <Badge variant="secondary" className="gap-1 font-normal">
              <FileCode2 className="size-3" />
              {entitiesCount} entities
            </Badge>
          )}
          {photosCount !== null && photosCount > 0 && (
            <Badge variant="secondary" className="gap-1 font-normal">
              <ImageIcon className="size-3 text-primary" />
              {photosCount} photos
            </Badge>
          )}
          {assumptionsCount > 0 && (
            <Badge variant="secondary" className="gap-1 font-normal">
              <Sparkles className="size-3 text-warning" />
              {assumptionsCount} assumptions
            </Badge>
          )}
        </Stack>
      </CardContent>
    </Card>
  );
}
