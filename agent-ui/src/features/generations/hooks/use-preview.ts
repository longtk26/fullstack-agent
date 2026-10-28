"use client";

import { useCallback, useRef } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { ApiError } from "@/lib/api-client";
import { fetchPreview, previewAction, recheckIntegration, sendUseMocksIntegration } from "../api/generations-api";
import { generationKeys } from "../query-keys";
import type { TPreview, TPreviewAction } from "../types";

const TOUCH_EVERY_MS = 60_000;
const ACTION_LABEL: Record<TPreviewAction, string> = {
  start: "Starting the preview",
  stop: "Stopping the preview",
  restart: "Restarting the preview",
  "reset-db": "Resetting the preview database",
  touch: "Extending the preview",
};

/** The generation's preview container: status (polled while it changes), actions and a debounced keep-alive. */
export function usePreview(id: string, initial: TPreview | null, kind: "backend" | "frontend" = "backend") {
  const queryClient = useQueryClient();
  const lastTouch = useRef(0);

  const preview = useQuery({
    queryKey: generationKeys.preview(id, kind),
    queryFn: async () => {
      try {
        return await fetchPreview(id, kind);
      } catch (error) {
        if (error instanceof ApiError && error.status === 404) return null;
        throw error;
      }
    },
    initialData: initial,
    refetchInterval: (query) => (query.state.data?.status === "STARTING" ? 2000 : 15_000),
  });

  const action = useMutation({
    mutationFn: (name: TPreviewAction) => previewAction(id, name, kind),
    onMutate: (name) => {
      if (name !== "touch") toast.info(`${ACTION_LABEL[name]}…`);
    },
    onSuccess: (data) => {
      queryClient.setQueryData(generationKeys.preview(id, kind), data);
      void queryClient.invalidateQueries({ queryKey: generationKeys.detail(id) });
    },
    onError: (error, name) => {
      if (name !== "touch") toast.error(error.message);
    },
  });

  const recheck = useMutation({
    mutationFn: () => recheckIntegration(id),
    onMutate: () => toast.info("Checking backend readiness…"),
    onSuccess: (data) => {
      toast.success("Integration re-checked");
      queryClient.setQueryData(generationKeys.preview(id, "frontend"), data);
      void queryClient.invalidateQueries({ queryKey: generationKeys.detail(id) });
    },
    onError: (error) => toast.error(error.message),
  });

  const useMocks = useMutation({
    mutationFn: () => sendUseMocksIntegration(id),
    onMutate: () => toast.info("Switching to mock API…"),
    onSuccess: (data) => {
      toast.success("Switched to mock API");
      queryClient.setQueryData(generationKeys.preview(id, "frontend"), data);
      void queryClient.invalidateQueries({ queryKey: generationKeys.detail(id) });
    },
    onError: (error) => toast.error(error.message),
  });

  const { mutate } = action;
  const touch = useCallback(() => {
    if (Date.now() - lastTouch.current < TOUCH_EVERY_MS) return;
    lastTouch.current = Date.now();
    mutate("touch");
  }, [mutate]);

  return {
    preview: preview.data ?? null,
    run: (name: TPreviewAction) => mutate(name),
    pending: action.isPending ? action.variables : null,
    recheck: () => recheck.mutate(),
    isRechecking: recheck.isPending,
    useMocks: () => useMocks.mutate(),
    isUsingMocks: useMocks.isPending,
    touch,
  };
}
