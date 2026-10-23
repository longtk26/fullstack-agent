"use client";

import { useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { zodResolver } from "@hookform/resolvers/zod";
import { useQueryClient } from "@tanstack/react-query";
import { useForm } from "react-hook-form";
import { loginAction } from "@/lib/auth-actions";
import { loginFormSchema, type TLoginFormValues } from "../schemas/login-schema";

function safeNext(next: string | null): string {
  return next && next.startsWith("/") && !next.startsWith("//") ? next : "/generations";
}

export function useLoginForm() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const queryClient = useQueryClient();
  const [formError, setFormError] = useState<string | null>(null);

  const form = useForm<TLoginFormValues>({
    resolver: zodResolver(loginFormSchema),
    defaultValues: { email: "", password: "" },
  });

  const handleSubmit = form.handleSubmit(async ({ email, password }) => {
    setFormError(null);
    const result = await loginAction(email, password);
    if (!result.ok) {
      setFormError(result.message);
      return;
    }
    queryClient.clear();
    router.replace(safeNext(searchParams.get("next")));
  });

  return { form, handleSubmit, formError, isSubmitting: form.formState.isSubmitting };
}
