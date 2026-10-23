"use client";

import { useEffect, useRef } from "react";
import type { BaseSyntheticEvent } from "react";
import { useRouter } from "next/navigation";
import { zodResolver } from "@hookform/resolvers/zod";
import { useForm } from "react-hook-form";
import { toast } from "sonner";
import { useEngines } from "@/features/specs/hooks/use-spec-queries";
import { ApiError } from "@/lib/api-client";
import {
  ENGINE_NAMES,
  generationOptionsSchema,
  type TGenerationOptionsFormValues,
} from "../schemas/generation-options-schema";
import { useCreateGeneration } from "./use-generation-mutations";

const DEFAULT_OPTIONS: TGenerationOptionsFormValues = {
  engine: "claude_code",
  maxRepairAttempts: 3,
  runTests: true,
  generateDockerfile: true,
  deployPreview: true,
};

function isEngineName(value: string): value is TGenerationOptionsFormValues["engine"] {
  return (ENGINE_NAMES as readonly string[]).includes(value);
}

/**
 * Options form + submit. The Idempotency-Key is reused while the payload is unchanged, so a double click
 * (or a retry after a network error) cannot create two generations.
 */
export function useNewGeneration(spec: unknown, canSubmit: boolean, onCreated: () => void) {
  const router = useRouter();
  const engines = useEngines();
  const create = useCreateGeneration();
  const lastSubmission = useRef<{ body: string; key: string } | null>(null);

  const form = useForm<TGenerationOptionsFormValues>({
    resolver: zodResolver(generationOptionsSchema),
    defaultValues: DEFAULT_OPTIONS,
  });

  const defaultEngine = engines.data?.default;
  useEffect(() => {
    if (defaultEngine && isEngineName(defaultEngine) && !form.formState.dirtyFields.engine) {
      form.setValue("engine", defaultEngine);
    }
  }, [defaultEngine, form]);

  const submitOptions = async (options: TGenerationOptionsFormValues) => {
    if (!canSubmit) return;
    const payload = { backendSpec: spec, options };
    const body = JSON.stringify(payload);
    if (lastSubmission.current?.body !== body) {
      lastSubmission.current = { body, key: crypto.randomUUID() };
    }
    try {
      const created = await create.mutateAsync({ payload, idempotencyKey: lastSubmission.current.key });
      onCreated();
      router.push(`/generations/${created.generationId}`);
    } catch (error) {
      toast.error(error instanceof ApiError ? `${error.code}: ${error.message}` : "Could not start the generation");
    }
  };
  const handleSubmit = (event?: BaseSyntheticEvent) => form.handleSubmit(submitOptions)(event);

  return {
    form,
    handleSubmit,
    engines: engines.data?.engines ?? [],
    enginesReportedByWorker: engines.data?.reportedByWorker ?? true,
    isSubmitting: create.isPending,
  };
}
