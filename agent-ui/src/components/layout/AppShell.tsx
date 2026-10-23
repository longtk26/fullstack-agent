import type { ReactNode } from "react";
import Link from "next/link";
import { Boxes, FilePlus2, ListChecks } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Separator } from "@/components/ui/separator";
import { Stack } from "@/components/layout/Stack";

type AppShellProps = {
  children: ReactNode;
};

const navItems = [
  { label: "Generations", icon: ListChecks },
  { label: "New generation", icon: FilePlus2 },
];

export function AppShell({ children }: AppShellProps) {
  return (
    <div className="flex min-h-screen bg-background text-foreground">
      <aside className="hidden w-60 shrink-0 border-r border-border bg-sidebar md:block">
        <Stack gap="lg" className="p-4">
          <Link href="/" className="flex items-center gap-2 font-semibold">
            <Boxes className="size-5 text-primary" />
            <span>Backend Gen Agent</span>
          </Link>
          <Separator />
          <nav>
            <Stack gap="xs">
            {navItems.map(({ label, icon: Icon }) => (
              <span
                key={label}
                className="flex items-center justify-between rounded-md px-2 py-1.5 text-sm text-muted-foreground"
              >
                <span className="flex items-center gap-2">
                  <Icon className="size-4" />
                  {label}
                </span>
                <Badge variant="outline">Soon</Badge>
              </span>
            ))}
            </Stack>
          </nav>
        </Stack>
      </aside>
      <div className="flex min-w-0 flex-1 flex-col">
        <header className="flex h-14 items-center border-b border-border px-4 sm:px-6">
          <span className="text-sm text-muted-foreground">Generate FastAPI backends from specs</span>
        </header>
        <main className="flex-1 py-8">{children}</main>
      </div>
    </div>
  );
}
