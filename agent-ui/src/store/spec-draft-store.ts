import { useSyncExternalStore } from "react";
import { create } from "zustand";
import { createJSONStorage, devtools, persist } from "zustand/middleware";
import type { TGenerationMode } from "@/features/generations/types";
import type { TSpecTab } from "@/features/specs/types";

/** The requirement draft whose specs were opened in the editors; sent as `draftId` so the requirement is kept. */
type TAppliedDraft = { id: string; mode: TGenerationMode };

type TSpecDraftState = {
  mode: TGenerationMode;
  specText: string;
  frontendSpecText: string;
  activeTab: TSpecTab;
  requirementText: string;
  requirementFileName: string | null;
  draftId: string | null;
  appliedDraft: TAppliedDraft | null;
  setMode: (mode: TGenerationMode) => void;
  setSpecText: (text: string) => void;
  setFrontendSpecText: (text: string) => void;
  setActiveTab: (tab: TSpecTab) => void;
  setRequirement: (text: string, fileName?: string | null) => void;
  setDraftId: (draftId: string | null) => void;
  setAppliedDraft: (draft: TAppliedDraft | null) => void;
  clearDraft: () => void;
};

/**
 * Per-browser draft of the generation being set up: the mode, both spec texts, the requirement and the requirement
 * draft job (so a reload keeps polling it) are persisted.
 */
export const useSpecDraftStore = create<TSpecDraftState>()(
  devtools(
    persist(
      (set) => ({
        mode: "backend",
        specText: "",
        frontendSpecText: "",
        activeTab: "json",
        requirementText: "",
        requirementFileName: null,
        draftId: null,
        appliedDraft: null,
        setMode: (mode) => set({ mode }, false, "specDraft/setMode"),
        setSpecText: (specText) => set({ specText }, false, "specDraft/setSpecText"),
        setFrontendSpecText: (frontendSpecText) => set({ frontendSpecText }, false, "specDraft/setFrontendSpecText"),
        setActiveTab: (activeTab) => set({ activeTab }, false, "specDraft/setActiveTab"),
        setRequirement: (requirementText, requirementFileName = null) =>
          set({ requirementText, requirementFileName }, false, "specDraft/setRequirement"),
        setDraftId: (draftId) => set({ draftId }, false, "specDraft/setDraftId"),
        setAppliedDraft: (appliedDraft) => set({ appliedDraft }, false, "specDraft/setAppliedDraft"),
        clearDraft: () =>
          set(
            { specText: "", frontendSpecText: "", requirementText: "", requirementFileName: null, draftId: null, appliedDraft: null },
            false,
            "specDraft/clearDraft",
          ),
      }),
      {
        name: "bga-spec-draft",
        storage: createJSONStorage(() => localStorage),
        partialize: (state) => ({
          mode: state.mode,
          specText: state.specText,
          frontendSpecText: state.frontendSpecText,
          requirementText: state.requirementText,
          requirementFileName: state.requirementFileName,
          draftId: state.draftId,
          appliedDraft: state.appliedDraft,
        }),
        // Rehydrated after mount (see NewGenerationView) so the server and first client render match.
        skipHydration: true,
      },
    ),
    { name: "spec-draft-store" },
  ),
);

/** True once the persisted draft is loaded; writing before that would persist the empty initial state over it. */
export function useSpecDraftHydrated() {
  return useSyncExternalStore(
    (onChange) => useSpecDraftStore.persist.onFinishHydration(onChange),
    () => useSpecDraftStore.persist.hasHydrated(),
    () => false,
  );
}
