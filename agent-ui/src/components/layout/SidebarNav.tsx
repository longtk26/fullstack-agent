"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { ChartColumn, FilePlus2, ListChecks } from "lucide-react";
import { Stack } from "@/components/layout/Stack";
import { cn } from "@/lib/utils";

const navItems = [
  { label: "Generations", href: "/generations", icon: ListChecks },
  { label: "New generation", href: "/generations/new", icon: FilePlus2 },
  { label: "Usage & traces", href: "/usage", icon: ChartColumn },
];

function isActive(pathname: string | null, href: string): boolean {
  if (!pathname) return false;
  if (href === "/generations") return pathname === href || /^\/generations\/(?!new)[^/]+/.test(pathname);
  return pathname.startsWith(href);
}

type NavLinksProps = {
  pathname: string | null;
};

/** The links alone; rendered without an active item while the pathname streams in. */
export function NavLinks({ pathname }: NavLinksProps) {
  return (
    <nav>
      <Stack gap="xs">
        {navItems.map(({ label, href, icon: Icon }) => (
          <Link
            key={href}
            href={href}
            className={cn(
              "flex items-center gap-2 rounded-md px-2 py-1.5 text-sm text-muted-foreground transition-colors hover:bg-sidebar-accent hover:text-sidebar-accent-foreground",
              isActive(pathname, href) && "bg-sidebar-accent font-medium text-sidebar-accent-foreground",
            )}
          >
            <Icon className="size-4" />
            {label}
          </Link>
        ))}
      </Stack>
    </nav>
  );
}

export function SidebarNav() {
  return <NavLinks pathname={usePathname()} />;
}
