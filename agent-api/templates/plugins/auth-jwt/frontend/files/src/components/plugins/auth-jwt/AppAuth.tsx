"use client";

import { useQueryClient } from "@tanstack/react-query";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { app } from "@/components/app/app";
import { AppFormBody } from "@/components/app/AppForm";
import type { TSectionSlot } from "@/components/app/plugin-types";
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from "@/components/ui/card";
import { nextPath, SESSION_KEY, signIn, signUp } from "./session";

/** Sign-in and sign-up (Story 22.7): the form kit on the auth operations' requests; back to the page the user came
 *  from. The sign-in page lists the demo accounts the backend seeds. */
export const AppAuth: TSectionSlot = ({ section }) => {
  const router = useRouter();
  const queryClient = useQueryClient();
  const auth = app.auth;
  const signingUp = section.content?.variant === "signUp";
  if (!auth || !section.form) return null;
  const other = signingUp ? auth.signIn : auth.signUp;
  return (
    <div className="mx-auto flex w-full max-w-sm flex-col gap-6 pt-6">
      <Card>
        <CardHeader>
          <CardTitle>
            <h1 className="text-xl font-semibold tracking-tight">{section.content?.title ?? (signingUp ? "Create an account" : "Sign in")}</h1>
          </CardTitle>
          <CardDescription>{signingUp ? `Join ${app.name}.` : `Welcome back to ${app.name}.`}</CardDescription>
        </CardHeader>
        <CardContent>
          <AppFormBody
            formId={section.form}
            submit={signingUp ? signUp : signIn}
            onDone={async () => {
              await queryClient.invalidateQueries();
              router.replace(nextPath());
            }}
          />
        </CardContent>
        {other && (
          <CardFooter className="justify-center text-sm text-muted-foreground">
            {signingUp ? "Already have an account?" : "New here?"}
            <Link href={other} className="ml-1 font-medium text-foreground underline-offset-4 hover:underline">
              {signingUp ? "Sign in" : "Create an account"}
            </Link>
          </CardFooter>
        )}
      </Card>
      {!signingUp && auth.demoUsers.length > 0 && (
        <div className="rounded-lg border border-dashed p-4 text-sm text-muted-foreground" data-bga-demo-accounts>
          <p className="font-medium text-foreground">Demo accounts</p>
          <ul className="mt-2 flex flex-col gap-1">
            {auth.demoUsers.map((user) => (
              <li key={user.login} className="flex items-center justify-between gap-2">
                <span className="truncate font-mono text-xs">{user.login}</span>
                <span className="text-xs">{user.role}</span>
              </li>
            ))}
          </ul>
          {auth.password && <p className="mt-2 text-xs">Password: <span className="font-mono">{auth.password}</span></p>}
        </div>
      )}
    </div>
  );
};
