import { Suspense } from "react";
import type { ReactNode } from "react";
import Link from "next/link";
import { Boxes } from "lucide-react";
import { Separator } from "@/components/ui/separator";
import { Stack } from "@/components/layout/Stack";
import { NavLinks, SidebarNav } from "@/components/layout/SidebarNav";
import { UserMenu } from "@/features/auth/components/UserMenu";

type AppShellProps = {
  children: ReactNode;
};

export function AppShell({ children }: AppShellProps) {
  return (
    <div className="flex min-h-screen bg-background text-foreground">
      <aside className="hidden w-60 shrink-0 border-r border-border bg-sidebar md:block">
        <Stack gap="lg" className="sticky top-0 p-4">
          <Link href="/generations" className="flex items-center gap-2 font-semibold">
            <Boxes className="size-5 text-primary" />
            <span>Backend Gen Agent</span>
          </Link>
          <Separator />
          <Suspense fallback={<NavLinks pathname={null} />}>
            <SidebarNav />
          </Suspense>
        </Stack>
      </aside>
      <div className="flex min-w-0 flex-1 flex-col">
        <header className="flex h-14 items-center justify-between gap-4 border-b border-border px-4 sm:px-6">
          <Link href="/generations" className="flex items-center gap-2 font-semibold md:hidden">
            <Boxes className="size-5 text-primary" />
          </Link>
          <span className="hidden text-sm text-muted-foreground md:block">Generate FastAPI backends from specs</span>
          <UserMenu />
        </header>
        <main className="flex-1 py-6">{children}</main>
      </div>
    </div>
  );
}
