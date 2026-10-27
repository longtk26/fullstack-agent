"use client";

import { useCallback } from "react";
import { toast } from "sonner";
import { fetchExampleText } from "../api/specs-api";
import { EXAMPLE_PAIRS } from "../lib/spec-kinds";
import { useExampleIndex } from "./use-spec-queries";

/** After a dynamic FrontendSpec example is loaded, offers to load the BackendSpec example it was written against. */
export function useExamplePairOffer(loadBackendSpec: (text: string) => void) {
  const { data: examples } = useExampleIndex();

  return useCallback(
    (frontendExample: string) => {
      const pairName = EXAMPLE_PAIRS[frontendExample];
      const pair = examples?.specs?.find((example) => example.name === pairName);
      if (!pair) return;
      toast(`Load its BackendSpec too?`, {
        description: `${frontendExample} is written against the ${pair.name} BackendSpec.`,
        duration: 15_000,
        action: {
          label: `Load ${pair.name}`,
          onClick: async () => {
            try {
              loadBackendSpec(await fetchExampleText(pair.path));
            } catch (error) {
              toast.error(error instanceof Error ? error.message : "Could not load the example");
            }
          },
        },
      });
    },
    [examples, loadBackendSpec],
  );
}
