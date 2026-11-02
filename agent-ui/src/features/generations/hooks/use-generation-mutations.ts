"use client";

import { useMutation, useQueryClient } from "@tanstack/react-query";
import { specKeys } from "@/features/specs/query-keys";
import { cancelGeneration, continueGeneration, createGeneration } from "../api/generations-api";
import { generationKeys } from "../query-keys";
import type { TCreateGenerationPayload, TGenerationDetail } from "../types";

export function useCreateGeneration() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ payload, idempotencyKey }: { payload: TCreateGenerationPayload; idempotencyKey: string }) =>
      createGeneration(payload, idempotencyKey),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: generationKeys.lists() }),
  });
}

export function useCancelGeneration(id: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: () => cancelGeneration(id),
    onSuccess: (result) => {
      queryClient.setQueryData<TGenerationDetail>(generationKeys.detail(id), (detail) =>
        detail ? { ...detail, cancelRequested: result.cancelRequested } : detail,
      );
      queryClient.invalidateQueries({ queryKey: generationKeys.detail(id) });
      queryClient.invalidateQueries({ queryKey: generationKeys.lists() });
    },
  });
}

type TContinuePayload = { backendSpec: Record<string, unknown> | null; frontendSpec: Record<string, unknown> | null };

/** Continues a NEEDS_REVIEW generation with fixed specs; the detail, its events and the draft refetch. */
export function useContinueGeneration(id: string, draftId: string | null) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (payload: TContinuePayload) => continueGeneration(id, payload),
    onSuccess: () =>
      Promise.all([
        queryClient.invalidateQueries({ queryKey: generationKeys.detail(id) }),
        queryClient.invalidateQueries({ queryKey: generationKeys.events(id) }),
        queryClient.invalidateQueries({ queryKey: generationKeys.lists() }),
        draftId ? queryClient.invalidateQueries({ queryKey: specKeys.draft(draftId) }) : undefined,
      ]),
  });
}
