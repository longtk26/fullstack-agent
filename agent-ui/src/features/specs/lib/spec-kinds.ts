import type { TExampleIndex, TSpecKind } from "../types";

type TSpecKindInfo = {
  label: string;
  /** Monaco model path, also the download name. */
  fileName: string;
  exampleKey: keyof TExampleIndex;
};

export const SPEC_KINDS: Record<TSpecKind, TSpecKindInfo> = {
  backend: { label: "BackendSpec", fileName: "backend-spec.json", exampleKey: "specs" },
  frontend: { label: "FrontendSpec", fileName: "frontend-spec.json", exampleKey: "frontend-specs" },
};

/** Dynamic FrontendSpec examples → the BackendSpec example they were written against (same file name, no `.json`). */
export const EXAMPLE_PAIRS: Record<string, string> = {
  "project-tracker-dynamic": "two-entity",
  "shop-dynamic": "shop",
};
