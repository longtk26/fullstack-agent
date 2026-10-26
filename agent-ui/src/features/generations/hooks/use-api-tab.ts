"use client";

import { useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { fetchArtifactJson } from "../api/generations-api";
import { generationKeys } from "../query-keys";
import type { TGenerationDetail, TManifest } from "../types";
import { usePreview } from "./use-preview";

type TOpenApiOperation = { operationId?: string; description?: string };
type TOpenApiDocument = { paths?: Record<string, Record<string, TOpenApiOperation>> };

/** Appends the frontend components bound to each operation (imported site JSON) to its description. */
function withBindings(document: TOpenApiDocument, manifest: TManifest | undefined): TOpenApiDocument {
  const bindings = manifest?.frontendBindings ?? [];
  if (bindings.length === 0) return document;
  const copy = structuredClone(document);
  for (const item of Object.values(copy.paths ?? {})) {
    for (const operation of Object.values(item)) {
      const bound = bindings.filter((binding) => binding.operationId === operation?.operationId);
      if (!operation || bound.length === 0) continue;
      const lines = bound.map((b) => `- \`${b.component}\` on page \`${b.page}\``).join("\n");
      operation.description = `${operation.description ?? ""}\n\n**Used by the frontend:**\n${lines}`.trim();
    }
  }
  return copy;
}

export function useApiTab(detail: TGenerationDetail) {
  const id = detail.generationId;
  const preview = usePreview(id, detail.preview);
  const [logsOpen, setLogsOpen] = useState(false);
  const openapiArtifact = detail.artifacts.find((artifact) => artifact.name === "openapi.json");
  const manifestArtifact = detail.artifacts.find((artifact) => artifact.name === "manifest.json");

  const openapi = useQuery({
    queryKey: generationKeys.artifact(id, openapiArtifact?.artifactId ?? ""),
    queryFn: () => fetchArtifactJson<TOpenApiDocument>(id, openapiArtifact!.artifactId),
    enabled: Boolean(openapiArtifact),
    staleTime: Infinity,
  });
  const manifest = useQuery({
    queryKey: generationKeys.artifact(id, manifestArtifact?.artifactId ?? ""),
    queryFn: () => fetchArtifactJson<TManifest>(id, manifestArtifact!.artifactId),
    enabled: Boolean(manifestArtifact),
    staleTime: Infinity,
  });
  const document = useMemo(
    () => (openapi.data ? withBindings(openapi.data, manifest.data) : null),
    [openapi.data, manifest.data],
  );

  return {
    ...preview,
    canPreview: detail.status === "COMPLETED" && detail.artifacts.some((a) => a.name === "backend.zip"),
    hasOpenapi: Boolean(openapiArtifact),
    document,
    loadingDocument: openapi.isLoading,
    logsOpen,
    setLogsOpen,
  };
}
