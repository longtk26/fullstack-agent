import { z } from "zod";

// Epic 24: `antigravity_json` / `claude_code_json` draft in one CLI turn with structured output (no per-token cost).
export const ENGINE_NAMES = [
  "claude_code",
  "antigravity",
  "antigravity_json",
  "claude_code_json",
  "gemini_api",
  "fake",
] as const;

export const generationOptionsSchema = z
  .object({
    engine: z.enum(ENGINE_NAMES),
    // Story 18.10: the engine that drafts specs from a requirement (an API engine by default; it writes no code).
    draftEngine: z.enum(ENGINE_NAMES),
    maxRepairAttempts: z.number().int().min(1, "At least 1").max(10, "At most 10"),
    runTests: z.boolean(),
    generateDockerfile: z.boolean(),
    deployPreview: z.boolean(),
    // Frontend lane (static and dynamic modes); not sent for backend-only generations.
    frontend: z.object({
      runTests: z.boolean(),
      generatePreview: z.boolean(),
      mockApi: z.boolean(),
    }),
  })
  // Mirrors the API's OPTIONS_CONFLICT rule.
  .refine((options) => !options.deployPreview || options.generateDockerfile, {
    path: ["deployPreview"],
    message: "A preview container needs the Dockerfile",
  });

export type TGenerationOptionsFormValues = z.infer<typeof generationOptionsSchema>;
