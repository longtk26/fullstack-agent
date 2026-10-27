import { z } from "zod";

export const ENGINE_NAMES = ["claude_code", "antigravity", "fake"] as const;

export const generationOptionsSchema = z
  .object({
    engine: z.enum(ENGINE_NAMES),
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
