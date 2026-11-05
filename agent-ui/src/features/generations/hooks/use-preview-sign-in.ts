"use client";

import { useState } from "react";
import { zodResolver } from "@hookform/resolvers/zod";
import { useForm } from "react-hook-form";
import { previewSignInSchema, type TPreviewSignInValues } from "../schemas/preview-sign-in-schema";
import type { TManifestAuth } from "../types";

/** Story 10.2 (the 9.6 helper): signs in to the running preview with the generated login and keeps the bearer token
 * for the try-it explorer. The call goes from the browser straight to the preview, as the explorer's do. */
export function usePreviewSignIn(auth: TManifestAuth | undefined, serverUrl: string | null) {
  const demo = auth?.demoUsers?.[0];
  const [token, setToken] = useState<string | null>(null);
  const [signedInAs, setSignedInAs] = useState<string | null>(null);
  const [formError, setFormError] = useState<string | null>(null);
  const form = useForm<TPreviewSignInValues>({
    resolver: zodResolver(previewSignInSchema),
    defaultValues: { login: demo?.login ?? "", password: demo?.password ?? "" },
  });

  const handleSubmit = form.handleSubmit(async ({ login, password }) => {
    if (!auth?.login || !serverUrl) return;
    setFormError(null);
    try {
      const response = await fetch(`${serverUrl}${auth.login.path}`, {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({ [auth.login.loginField]: login, password }),
      });
      const body = (await response.json().catch(() => null)) as
        | { accessToken?: string; error?: { message?: string } }
        | null;
      if (!response.ok || !body?.accessToken) {
        setFormError(body?.error?.message ?? `Sign-in failed (HTTP ${response.status})`);
        return;
      }
      setToken(body.accessToken);
      setSignedInAs(login);
    } catch {
      setFormError("The preview did not answer");
    }
  });

  const pickDemo = (login: string) => {
    const user = auth?.demoUsers?.find((candidate) => candidate.login === login);
    if (user) form.reset({ login: user.login, password: user.password });
  };

  const signOut = () => {
    setToken(null);
    setSignedInAs(null);
  };

  return { form, handleSubmit, formError, isSubmitting: form.formState.isSubmitting, token, signedInAs, pickDemo, signOut };
}
