"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { ApiError } from "@/lib/api-client";
import { fetchEvaluation, runEvaluation } from "../api/generations-api";
import { generationKeys } from "../query-keys";

/** Story 26.6: the latest business evaluation, polled while it runs, and "Run again". `data` is null when the
 * generation has no bound business workflows (no Business tab). */
export function useEvaluation(id: string, enabled = true) {
  const queryClient = useQueryClient();
  const evaluation = useQuery({
    queryKey: generationKeys.evaluation(id),
    enabled,
    queryFn: async () => {
      try {
        return await fetchEvaluation(id);
      } catch (error) {
        if (error instanceof ApiError && error.status === 404) return null;
        throw error;
      }
    },
    refetchInterval: (query) => {
      const status = query.state.data?.status;
      return status === "PENDING" || status === "RUNNING" ? 3000 : 30_000;
    },
  });
  const run = useMutation({
    mutationFn: () => runEvaluation(id),
    onSuccess: (data) => {
      queryClient.setQueryData(generationKeys.evaluation(id), data);
      toast.success("The evaluation runs again");
    },
    onError: (error) => toast.error(error instanceof Error ? error.message : "Could not start the evaluation"),
  });
  return { evaluation, run };
}
