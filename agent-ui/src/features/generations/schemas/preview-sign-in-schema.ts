import { z } from "zod";

export const previewSignInSchema = z.object({
  login: z.string().trim().min(1, "Required"),
  password: z.string().min(1, "Password is required"),
});

export type TPreviewSignInValues = z.infer<typeof previewSignInSchema>;
