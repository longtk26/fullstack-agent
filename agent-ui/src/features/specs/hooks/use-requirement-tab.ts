"use client";

import { useState } from "react";
import { toast } from "sonner";
import type { TGenerationMode } from "@/features/generations/types";
import { ApiError } from "@/lib/api-client";
import { pickFile, prettyJson } from "@/lib/files";
import { useSpecDraftStore } from "@/store/spec-draft-store";
import { fetchExampleText } from "../api/specs-api";
import {
  REQUIREMENT_ACCEPT,
  REQUIREMENT_MAX_BYTES,
  REQUIREMENT_MIN_CHARS,
  readRequirementFile,
  requirementBytes,
} from "../lib/requirement-file";
import type { TExampleFile } from "../types";
import { FINISHED_DRAFT, useCreateSpecDraft, useExampleIndex, useSpecDraft } from "./use-spec-queries";

type TRequirementTabInput = {
  mode: TGenerationMode;
  engine: string | null;
};

/**
 * Requirement → draft spec(s) (Stories 2.4, 12.4): the requirement is typed or loaded from a `.md` / `.txt` file,
 * drafted on the worker (polled), reviewed (assumptions / unresolved acknowledged) and opened in the editors.
 */
export function useRequirementTab({ mode, engine }: TRequirementTabInput) {
  const text = useSpecDraftStore((state) => state.requirementText);
  const fileName = useSpecDraftStore((state) => state.requirementFileName);
  const setRequirement = useSpecDraftStore((state) => state.setRequirement);
  const draftId = useSpecDraftStore((state) => state.draftId);
  const setDraftId = useSpecDraftStore((state) => state.setDraftId);
  const setAppliedDraft = useSpecDraftStore((state) => state.setAppliedDraft);
  const setSpecText = useSpecDraftStore((state) => state.setSpecText);
  const setFrontendSpecText = useSpecDraftStore((state) => state.setFrontendSpecText);
  const setActiveTab = useSpecDraftStore((state) => state.setActiveTab);
  const [acknowledged, setAcknowledged] = useState(false);
  const { data: examples } = useExampleIndex();
  const create = useCreateSpecDraft();
  const draftQuery = useSpecDraft(draftId);

  const draft = draftQuery.data;
  const isFinished = Boolean(draft && FINISHED_DRAFT.includes(draft.status));
  const isRunning = Boolean(draftId) && !isFinished && !draftQuery.isError;
  const bytes = requirementBytes(text);
  const tooShort = text.trim().length < REQUIREMENT_MIN_CHARS;
  const tooLarge = bytes > REQUIREMENT_MAX_BYTES;
  const needsAcknowledgement = Boolean(draft && (draft.assumptions.length || draft.unresolved.length));

  const loadFile = async (file: File | null) => {
    if (!file) return;
    try {
      setRequirement(await readRequirementFile(file), file.name);
    } catch (error) {
      toast.error(error instanceof Error ? error.message : "Could not read the file");
    }
  };

  return {
    text,
    fileName,
    bytes,
    tooShort,
    tooLarge,
    examples: examples?.requirements ?? [],
    draft,
    draftError: draftQuery.error,
    isRunning,
    isFinished,
    isStarting: create.isPending,
    canDraft: !tooShort && !tooLarge && !create.isPending && !isRunning,
    needsAcknowledgement,
    acknowledged,
    setAcknowledged,
    setText: (next: string) => setRequirement(next, fileName),
    clearFile: () => setRequirement(text, null),
    loadFile,
    upload: async () => loadFile(await pickFile(REQUIREMENT_ACCEPT)),
    loadExample: async (example: TExampleFile) => {
      try {
        setRequirement(await fetchExampleText(example.path), `${example.name}.md`);
      } catch (error) {
        toast.error(error instanceof Error ? error.message : "Could not load the example");
      }
    },
    startDraft: async () => {
      try {
        const created = await create.mutateAsync({ mode, requirementText: text, requirementFileName: fileName, engine });
        setAcknowledged(false);
        setDraftId(created.draftId);
      } catch (error) {
        toast.error(error instanceof ApiError ? `${error.code}: ${error.message}` : "Could not start the draft");
      }
    },
    discardDraft: () => setDraftId(null),
    openInEditor: () => {
      if (!draft) return;
      if (draft.backendSpec) setSpecText(prettyJson(draft.backendSpec));
      if (draft.frontendSpec) setFrontendSpecText(prettyJson(draft.frontendSpec));
      setAppliedDraft({ id: draft.draftId, mode: draft.mode });
      setActiveTab(draft.mode === "backend" ? "json" : "frontend");
      toast.success("Draft opened in the editor");
    },
  };
}

export type TRequirementTab = ReturnType<typeof useRequirementTab>;
