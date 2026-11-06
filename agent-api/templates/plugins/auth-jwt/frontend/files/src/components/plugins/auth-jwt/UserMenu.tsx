"use client";

import { useQueryClient } from "@tanstack/react-query";
import { LogOut } from "lucide-react";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useEffect } from "react";
import { app } from "@/components/app/app";
import type { TUserMenu } from "@/components/app/plugin-types";
import { Badge } from "@/components/ui/badge";
import { Button, buttonVariants } from "@/components/ui/button";
import { DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuSeparator, DropdownMenuTrigger } from "@/components/ui/dropdown-menu";
import { onUnauthorized } from "@/lib/api/client";
import { clearToken } from "@/lib/auth/token";
import { SESSION_KEY, signOut, useSession } from "./session";
import { t } from "@/components/app/messages";

/** The top bar's account (Story 22.7): sign in and sign up when signed out; the user, their role and sign out when
 *  signed in. A 401 on a call (an expired session) signs the user out and asks them to sign in again. */
export const UserMenu: TUserMenu = () => {
  const session = useSession();
  const queryClient = useQueryClient();
  const router = useRouter();
  const pathname = usePathname();
  const auth = app.auth;

  useEffect(() => {
    onUnauthorized(() => {
      const signedIn = Boolean(queryClient.getQueryData(SESSION_KEY));
      clearToken();
      queryClient.setQueryData(SESSION_KEY, null);
      if (signedIn && auth) router.push(`${auth.signIn}?next=${encodeURIComponent(window.location.pathname)}`);
    });
    return () => onUnauthorized(null);
  }, [queryClient, router, auth]);

  if (!auth || !session.ready) return null;
  if (!session.user) {
    if (pathname === auth.signIn || pathname === auth.signUp) return null;
    const next = `?next=${encodeURIComponent(pathname)}`;
    return (
      <div className="flex items-center gap-1">
        <Link href={`${auth.signIn}${next}`} className={buttonVariants({ variant: "ghost", size: "sm" })} data-bga-action="sign-in">{t("signIn")}</Link>
        {auth.signUp && (
          <Link href={`${auth.signUp}${next}`} className={buttonVariants({ size: "sm" })} data-bga-action="sign-up">{t("signUp")}</Link>
        )}
      </div>
    );
  }
  const login = String(session.user[auth.loginField] ?? session.user.email ?? "");
  const initials = login.slice(0, 2).toUpperCase();
  return (
    <DropdownMenu>
      <DropdownMenuTrigger
        render={
          <Button variant="ghost" size="sm" className="gap-2" aria-label={t("account", { name: login })} data-bga-action="account">
            <span className="flex size-6 items-center justify-center rounded-full bg-primary text-[0.625rem] font-semibold text-primary-foreground">
              {initials}
            </span>
            <span className="hidden max-w-40 truncate sm:inline">{login}</span>
          </Button>
        }
      />
      <DropdownMenuContent align="end" className="min-w-56">
        <div className="flex flex-col gap-1 px-2 py-1.5">
          <span className="truncate text-sm font-medium">{login}</span>
          {session.user.role && (
            <Badge variant="secondary" className="w-fit">
              {String(session.user.role)}
            </Badge>
          )}
        </div>
        <DropdownMenuSeparator />
        <DropdownMenuItem
          data-bga-action="sign-out"
          onClick={async () => {
            await signOut();
            queryClient.clear();
            queryClient.setQueryData(SESSION_KEY, null);
            router.push("/");
          }}
        >
          <LogOut aria-hidden />{t("signOut")}</DropdownMenuItem>
      </DropdownMenuContent>
    </DropdownMenu>
  );
};
