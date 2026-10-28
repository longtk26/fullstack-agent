"use client";

import { useQuery } from "@tanstack/react-query";
import { fetchPreviewLogs, fetchPreviewRequests } from "../api/generations-api";
import { generationKeys } from "../query-keys";

/** Container logs and the request log, polled only while the drawer is open. */
export function usePreviewLogs(id: string, open: boolean, kind: "backend" | "frontend" = "backend") {
  const logs = useQuery({
    queryKey: generationKeys.previewLogs(id, kind),
    queryFn: () => fetchPreviewLogs(id, 300, kind),
    enabled: open,
    refetchInterval: open ? 3000 : false,
  });
  const requests = useQuery({
    queryKey: generationKeys.previewRequests(id),
    queryFn: () => fetchPreviewRequests(id),
    enabled: open,
    refetchInterval: open ? 3000 : false,
  });
  return { logs, requests: { ...requests, items: [...(requests.data?.items ?? [])].reverse() } };
}
