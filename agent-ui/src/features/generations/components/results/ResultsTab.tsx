"use client";

import type { ReactNode } from "react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { Stack } from "@/components/layout/Stack";
import { useResults } from "../../hooks/use-results";
import type { TGenerationDetail } from "../../types";
import { FrontendPreviewCard } from "../detail/FrontendPreviewCard";
import { ArtifactList } from "./ArtifactList";
import { ManifestPanel } from "./ManifestPanel";
import { MarkdownReport } from "./MarkdownReport";
import { SourceBrowser } from "./SourceBrowser";
import { ValidationHistory } from "./ValidationHistory";

type ResultsTabProps = {
  detail: TGenerationDetail;
  onOpenAppTab?: () => void;
};

export function ResultsTab({ detail, onOpenAppTab }: ResultsTabProps) {
  const results = useResults(detail);
  const id = detail.generationId;
  const hasFrontend = detail.mode === "static" || detail.mode === "dynamic";

  return (
    <Stack gap="lg">
      {hasFrontend && (
        <FrontendPreviewCard detail={detail} onOpenAppTab={onOpenAppTab} />
      )}
      {detail.status === "FAILED" && results.report.data && (
        <Section title="Diagnostic report" description="What failed, the last validation and the repair history.">
          <MarkdownReport markdown={results.report.data} />
        </Section>
      )}
      <div className="grid gap-6 xl:grid-cols-[minmax(0,3fr)_minmax(0,2fr)]">
        <Section
          title="Validation"
          description={
            results.validation.data?.attempts
              ? `${results.validation.data.attempts} attempt(s); expand a check for its findings`
              : "The eight sandbox checks"
          }
        >
          <ValidationHistory history={results.validation.data} loading={results.validation.isLoading} />
        </Section>
        <Section title="Artifacts" description="Downloads for this generation">
          <ArtifactList generationId={id} artifacts={results.artifacts} />
        </Section>
      </div>
      {results.manifest.data ? (
        <Section title="Manifest" description="The contract the generated backend implements">
          <ManifestPanel manifest={results.manifest.data} />
        </Section>
      ) : (
        results.manifest.isLoading && <Skeleton className="h-48 w-full" />
      )}
      {results.hasSource && (
        <Section title="Source" description="Read-only view of backend.zip">
          <SourceBrowser generationId={id} />
        </Section>
      )}
    </Stack>
  );
}

function Section({ title, description, children }: { title: string; description: string; children: ReactNode }) {
  return (
    <Card>
      <CardHeader>
        <CardTitle>{title}</CardTitle>
        <CardDescription>{description}</CardDescription>
      </CardHeader>
      <CardContent>{children}</CardContent>
    </Card>
  );
}
