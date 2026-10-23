"use client";

import { useMutation, useQueryClient } from "@tanstack/react-query";
import { cancelGeneration, createGeneration } from "../api/generations-api";
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
