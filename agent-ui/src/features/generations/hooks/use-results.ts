"use client";

import { useQuery } from "@tanstack/react-query";
import { fetchArtifactJson, fetchArtifactText, fetchValidationHistory } from "../api/generations-api";
import { isTerminal } from "../lib/status";
import { generationKeys } from "../query-keys";
import type { TArtifact, TGenerationDetail, TManifest } from "../types";

const ARTIFACT_ORDER = ["source", "openapi", "manifest", "report", "seed", "plan", "spec", "patch", "validation", "log"];

export function sortArtifacts(artifacts: TArtifact[]): TArtifact[] {
  const rank = (kind: string) => (ARTIFACT_ORDER.indexOf(kind) + 1 || ARTIFACT_ORDER.length + 1);
  return [...artifacts].sort((a, b) => rank(a.kind) - rank(b.kind) || a.name.localeCompare(b.name));
}

/** Data behind the Results tab: validation history, the manifest and (for failures) the rendered report. */
export function useResults(detail: TGenerationDetail) {
  const id = detail.generationId;
  const byName = new Map(detail.artifacts.map((artifact) => [artifact.name, artifact]));
  const manifestArtifact = byName.get("manifest.json");
  const reportArtifact = byName.get("report.md");
  const running = !isTerminal(detail.status);

  const validation = useQuery({
    queryKey: generationKeys.validation(id),
    queryFn: () => fetchValidationHistory(id),
    refetchInterval: running ? 5000 : false,
  });
  const manifest = useQuery({
    queryKey: generationKeys.artifact(id, manifestArtifact?.artifactId ?? ""),
    queryFn: () => fetchArtifactJson<TManifest>(id, manifestArtifact!.artifactId),
    enabled: Boolean(manifestArtifact),
    staleTime: Infinity,
  });
  const report = useQuery({
    queryKey: generationKeys.artifact(id, reportArtifact?.artifactId ?? ""),
    queryFn: () => fetchArtifactText(id, reportArtifact!.artifactId),
    enabled: Boolean(reportArtifact) && detail.status === "FAILED",
    staleTime: Infinity,
  });

  return {
    artifacts: sortArtifacts(detail.artifacts),
    hasSource: byName.has("backend.zip"),
    validation,
    manifest,
    report,
  };
}
