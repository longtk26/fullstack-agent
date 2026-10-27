import { useSyncExternalStore } from "react";
import { create } from "zustand";
import { createJSONStorage, devtools, persist } from "zustand/middleware";
import type { TGenerationMode } from "@/features/generations/types";
import type { TSpecTab } from "@/features/specs/types";

type TSpecDraftState = {
  mode: TGenerationMode;
  specText: string;
  frontendSpecText: string;
  activeTab: TSpecTab;
  setMode: (mode: TGenerationMode) => void;
  setSpecText: (text: string) => void;
  setFrontendSpecText: (text: string) => void;
  setActiveTab: (tab: TSpecTab) => void;
  clearDraft: () => void;
};

/** Per-browser draft of the generation being set up: the mode and both spec texts are persisted. */
export const useSpecDraftStore = create<TSpecDraftState>()(
  devtools(
    persist(
      (set) => ({
        mode: "backend",
        specText: "",
        frontendSpecText: "",
        activeTab: "json",
        setMode: (mode) => set({ mode }, false, "specDraft/setMode"),
        setSpecText: (specText) => set({ specText }, false, "specDraft/setSpecText"),
        setFrontendSpecText: (frontendSpecText) => set({ frontendSpecText }, false, "specDraft/setFrontendSpecText"),
        setActiveTab: (activeTab) => set({ activeTab }, false, "specDraft/setActiveTab"),
        clearDraft: () => set({ specText: "", frontendSpecText: "" }, false, "specDraft/clearDraft"),
      }),
      {
        name: "bga-spec-draft",
        storage: createJSONStorage(() => localStorage),
        partialize: (state) => ({ mode: state.mode, specText: state.specText, frontendSpecText: state.frontendSpecText }),
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
