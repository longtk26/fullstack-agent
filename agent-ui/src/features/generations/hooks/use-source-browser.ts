"use client";

import { useState } from "react";
import { useQueries, useQuery } from "@tanstack/react-query";
import { fetchFiles } from "../api/generations-api";
import { generationKeys } from "../query-keys";
import type { TFileEntry } from "../types";

/** Lazy file tree over the packaged source: a directory is listed when it is expanded. */
export function useSourceBrowser(id: string, enabled: boolean) {
  const [expanded, setExpanded] = useState<string[]>([""]);
  const [selected, setSelected] = useState<string | null>("README.md");

  const listings = useQueries({
    queries: expanded.map((path) => ({
      queryKey: generationKeys.files(id, path),
      queryFn: () => fetchFiles(id, path),
      enabled,
      staleTime: Infinity,
    })),
  });
  const file = useQuery({
    queryKey: generationKeys.files(id, selected ?? ""),
    queryFn: () => fetchFiles(id, selected!),
    enabled: enabled && Boolean(selected),
    staleTime: Infinity,
    retry: false,
  });

  const children = new Map<string, TFileEntry[]>();
  expanded.forEach((path, index) => {
    const data = listings[index]?.data;
    if (data?.type === "dir") children.set(path, data.entries);
  });

  const toggle = (path: string) =>
    setExpanded((current) => (current.includes(path) ? current.filter((p) => p !== path) : [...current, path]));

  return {
    children,
    expanded: new Set(expanded),
    loadingRoot: listings[0]?.isLoading ?? false,
    rootError: listings[0]?.error ?? null,
    toggle,
    selected,
    select: setSelected,
    file,
  };
}
