"use client";

import { KeyRound } from "lucide-react";
import { Controller } from "react-hook-form";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Field, FieldError, FieldLabel } from "@/components/ui/field";
import { Input } from "@/components/ui/input";
import { Spinner } from "@/components/ui/spinner";
import type { TManifestAuth } from "../../types";
import type { usePreviewSignIn } from "../../hooks/use-preview-sign-in";

type PreviewSignInProps = {
  auth: TManifestAuth;
  live: boolean;
  signIn: ReturnType<typeof usePreviewSignIn>;
};

/** The generated API's sign-in, for the try-it explorer: demo users, a "Get token" form, the token in use. */
export function PreviewSignIn({ auth, live, signIn }: PreviewSignInProps) {
  const loginField = auth.login?.loginField ?? "email";
  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2 text-sm">
          <KeyRound className="size-4" />
          Sign in to the API
        </CardTitle>
        <CardDescription>
          Protected operations need a bearer token. The preview seeds a demo user per role (password{" "}
          <code>{auth.demoUsers?.[0]?.password}</code>).
        </CardDescription>
      </CardHeader>
      <CardContent className="flex flex-col gap-3">
        <div className="flex flex-wrap gap-2">
          {(auth.demoUsers ?? []).map((user) => (
            <Button key={user.login} type="button" size="sm" variant="outline" onClick={() => signIn.pickDemo(user.login)}>
              {user.login}
              <Badge variant="secondary">{user.role}</Badge>
            </Button>
          ))}
        </div>
        {signIn.signedInAs ? (
          <div className="flex items-center justify-between gap-2 text-sm">
            <span>
              Requests send the token of <strong>{signIn.signedInAs}</strong>.
            </span>
            <Button type="button" size="sm" variant="ghost" onClick={signIn.signOut}>
              Clear token
            </Button>
          </div>
        ) : (
          <form onSubmit={signIn.handleSubmit} noValidate className="grid gap-3 md:grid-cols-[1fr_1fr_auto] md:items-end">
            <Controller
              name="login"
              control={signIn.form.control}
              render={({ field, fieldState }) => (
                <Field data-invalid={fieldState.invalid}>
                  <FieldLabel htmlFor="preview-login">{loginField}</FieldLabel>
                  <Input {...field} id="preview-login" autoComplete="off" aria-invalid={fieldState.invalid} />
                  <FieldError errors={[fieldState.error]} />
                </Field>
              )}
            />
            <Controller
              name="password"
              control={signIn.form.control}
              render={({ field, fieldState }) => (
                <Field data-invalid={fieldState.invalid}>
                  <FieldLabel htmlFor="preview-password">Password</FieldLabel>
                  <Input {...field} id="preview-password" type="password" autoComplete="off" aria-invalid={fieldState.invalid} />
                  <FieldError errors={[fieldState.error]} />
                </Field>
              )}
            />
            <Button type="submit" disabled={!live || signIn.isSubmitting}>
              {signIn.isSubmitting && <Spinner />}
              Get token
            </Button>
          </form>
        )}
        {signIn.formError && (
          <Alert variant="destructive">
            <AlertDescription>{signIn.formError}</AlertDescription>
          </Alert>
        )}
        {!live && <p className="text-xs text-muted-foreground">Start the preview to sign in.</p>}
      </CardContent>
    </Card>
  );
}
