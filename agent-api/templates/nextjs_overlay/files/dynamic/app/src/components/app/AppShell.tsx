"use client";

import type { ReactNode } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { ThemeToggle } from "@/components/layout/ThemeToggle";
import {
  Sidebar,
  SidebarContent,
  SidebarGroup,
  SidebarGroupContent,
  SidebarHeader,
  SidebarInset,
  SidebarMenu,
  SidebarMenuButton,
  SidebarMenuItem,
  SidebarProvider,
  SidebarRail,
  SidebarTrigger,
} from "@/components/ui/sidebar";
import { siteConfig } from "@/config/site";
import { app, canUse, pageOperation } from "./app";
import { AppBreadcrumbs } from "./AppBreadcrumbs";
import { icons } from "./icons";
import { UserMenu, useSession } from "./plugins";

type AppShellProps = {
  children: ReactNode;
};

function active(pathname: string, href: string): boolean {
  return href === "/" ? pathname === "/" : pathname === href || pathname.startsWith(`${href}/`);
}

/** The app's one shell (Epic 22): the outline's navigation in a collapsible sidebar (a sheet on phones), a top bar
 *  with the page's place and the theme switch. */
export function AppShell({ children }: AppShellProps) {
  const pathname = usePathname();
  const session = useSession();
  const AppIcon = icons[app.icon];
  // Story 22.7: navigation the signed-in user's role cannot use is hidden
  const pages = Object.fromEntries(Object.entries(app.pages).map(([id, page]) => [page.route, id]));
  const nav = app.nav.filter((item) => canUse(pageOperation(pages[item.href] ?? ""), session));
  return (
    <SidebarProvider>
      <Sidebar collapsible="icon">
        <SidebarHeader>
          <SidebarMenu>
            <SidebarMenuItem>
              <SidebarMenuButton size="lg" render={<Link href="/" />}>
                <span className="flex size-8 shrink-0 items-center justify-center rounded-md bg-primary text-primary-foreground">
                  {AppIcon && <AppIcon className="size-4" aria-hidden />}
                </span>
                <span className="flex min-w-0 flex-col leading-tight">
                  <span className="truncate font-semibold">{app.name}</span>
                  {app.tagline && <span className="truncate text-xs text-muted-foreground">{app.tagline}</span>}
                </span>
              </SidebarMenuButton>
            </SidebarMenuItem>
          </SidebarMenu>
        </SidebarHeader>
        <SidebarContent>
          <SidebarGroup>
            <SidebarGroupContent>
              <SidebarMenu>
                {nav.map((item) => {
                  const Icon = icons[item.icon];
                  return (
                    <SidebarMenuItem key={item.href}>
                      <SidebarMenuButton
                        isActive={active(pathname, item.href)}
                        tooltip={item.label}
                        render={<Link href={item.href} />}
                      >
                        {Icon && <Icon aria-hidden />}
                        <span>{item.label}</span>
                      </SidebarMenuButton>
                    </SidebarMenuItem>
                  );
                })}
              </SidebarMenu>
            </SidebarGroupContent>
          </SidebarGroup>
        </SidebarContent>
        <SidebarRail />
      </Sidebar>
      <SidebarInset>
        <header className="sticky top-0 z-10 flex h-14 shrink-0 items-center gap-2 border-b bg-background/95 px-4 backdrop-blur">
          <SidebarTrigger className="-ml-1" />
          <AppBreadcrumbs />
          <div className="ml-auto flex items-center gap-1">
            {siteConfig.themeToggle && <ThemeToggle />}
            <UserMenu />
          </div>
        </header>
        <div className="flex-1 px-4 py-6 sm:px-6 lg:px-8">{children}</div>
      </SidebarInset>
    </SidebarProvider>
  );
}
