import { create } from "zustand";
import { createJSONStorage, devtools, persist } from "zustand/middleware";
import type { TSpecTab } from "@/features/specs/types";

type TSpecDraftState = {
  specText: string;
  activeTab: TSpecTab;
  setSpecText: (text: string) => void;
  setActiveTab: (tab: TSpecTab) => void;
  clearDraft: () => void;
};

/** Per-browser draft of the BackendSpec being edited. Only the spec text is persisted. */
export const useSpecDraftStore = create<TSpecDraftState>()(
  devtools(
    persist(
      (set) => ({
        specText: "",
        activeTab: "json",
        setSpecText: (specText) => set({ specText }, false, "specDraft/setSpecText"),
        setActiveTab: (activeTab) => set({ activeTab }, false, "specDraft/setActiveTab"),
        clearDraft: () => set({ specText: "" }, false, "specDraft/clearDraft"),
      }),
      {
        name: "bga-spec-draft",
        storage: createJSONStorage(() => localStorage),
        partialize: (state) => ({ specText: state.specText }),
        // Rehydrated after mount (see NewGenerationView) so the server and first client render match.
        skipHydration: true,
      },
    ),
    { name: "spec-draft-store" },
  ),
);
