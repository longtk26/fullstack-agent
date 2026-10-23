import { z } from "zod";

export const loginFormSchema = z.object({
  email: z.string().trim().regex(/^[^@\s]+@[^@\s]+$/, "Enter a valid email"),
  password: z.string().min(1, "Password is required"),
});

export type TLoginFormValues = z.infer<typeof loginFormSchema>;
