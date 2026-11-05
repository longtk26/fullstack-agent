import type { ReactNode } from "react";
import { AppShell } from "@/components/app/AppShell";

type SiteShellProps = {
  children: ReactNode;
};

/** The root layout's shell: in an app (Epic 22), the app kit's shell. */
export function SiteShell({ children }: SiteShellProps) {
  return <AppShell>{children}</AppShell>;
}
