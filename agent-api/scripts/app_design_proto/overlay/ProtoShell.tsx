"use client";

// Story 23.0 prototype only: the brief's shell (a top bar, with tabs or not, and bottom tabs on phones) and the look
// (`data-recipe` on <html>). The sidebar and rail shells are the kit's AppShell.
import { Search } from "lucide-react";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useEffect, useState, type ComponentType, type ReactNode } from "react";
import { ThemeToggle } from "@/components/layout/ThemeToggle";
import { Input } from "@/components/ui/input";
import { siteConfig } from "@/config/site";
import { cn } from "@/lib/utils";
import { app, canUse, pageOperation } from "./app";
import { useLayout, useProto, type TLayout } from "./design";
import { icons } from "./icons";
import { UserMenu, useSession } from "./plugins";

function active(pathname: string, href: string): boolean {
  return href === "/" ? pathname === "/" : pathname === href || pathname.startsWith(`${href}/`);
}

/** The main entity's list page and its section, for the top bar's search (`<section>.q`, as AppList reads it). */
function mainList(layout: TLayout, needSearch = true): { route: string; section: string } | null {
  for (const page of Object.values(app.pages)) {
    const section = page.sections.find((s) => s.component === "AppList" && s.content?.entity === layout.mainEntity);
    if (section && !page.route.includes("[") && page.route !== "/" && (!needSearch || section.content?.controls?.search))
      return { route: page.route, section: section.id };
  }
  return null;
}

function TopBar({ children, layout }: { children: ReactNode; layout: TLayout }) {
  const pathname = usePathname();
  const router = useRouter();
  const session = useSession();
  const [query, setQuery] = useState("");
  const AppIcon = icons[app.icon];
  const pages = Object.fromEntries(Object.entries(app.pages).map(([id, page]) => [page.route, id]));
  const nav = app.nav.filter((item) => canUse(pageOperation(pages[item.href] ?? ""), session));
  const search = mainList(layout);
  const tabs = layout.shell === "topbar-tabs";
  const bottom = layout.mobileNav === "bottom-tabs" && nav.length <= 5;
  const links = (className: string) =>
    nav.map((item) => {
      const Icon = icons[item.icon];
      return (
        <Link
          key={item.href}
          href={item.href}
          data-active={active(pathname, item.href) || undefined}
          className={cn(
            "flex items-center gap-2 rounded-md px-3 py-1.5 text-sm font-medium whitespace-nowrap text-muted-foreground transition-colors hover:text-foreground data-[active]:bg-accent data-[active]:text-foreground",
            className,
          )}
        >
          {Icon && <Icon className="size-4" aria-hidden />}
          {item.label}
        </Link>
      );
    });
  return (
    <div className="flex min-h-svh flex-col" data-proto-shell={layout.shell}>
      <header className="sticky top-0 z-20 border-b bg-background/80 backdrop-blur" data-proto="header">
        <div className="mx-auto flex h-16 w-full max-w-screen-2xl items-center gap-4 px-4 sm:px-6">
          <Link href="/" className="flex shrink-0 items-center gap-2 font-semibold">
            <span className="flex size-8 items-center justify-center rounded-md bg-primary text-primary-foreground" data-proto="logo">
              {AppIcon && <AppIcon className="size-4" aria-hidden />}
            </span>
            <span className="hidden sm:inline">{app.name}</span>
          </Link>
          {!tabs && <nav className="hidden items-center gap-1 lg:flex" aria-label="Main">{links("")}</nav>}
          {search && (
            <form
              role="search"
              className="relative mx-auto hidden w-full max-w-xl flex-1 sm:block"
              onSubmit={(event) => {
                event.preventDefault();
                router.push(`${search.route}?${encodeURIComponent(`${search.section}.q`)}=${encodeURIComponent(query)}`);
              }}
            >
              <Search className="pointer-events-none absolute top-1/2 left-3 size-4 -translate-y-1/2 text-muted-foreground" aria-hidden />
              <Input
                type="search"
                value={query}
                onChange={(event) => setQuery(event.target.value)}
                placeholder={`Search ${app.entities[layout.mainEntity]?.plural?.toLowerCase() ?? ""}`}
                aria-label="Search"
                className="h-10 rounded-full pl-9"
              />
            </form>
          )}
          <div className="ml-auto flex items-center gap-1">
            {siteConfig.themeToggle && <ThemeToggle />}
            <UserMenu />
          </div>
        </div>
        {(tabs || !bottom) && (
          <nav
            className={cn("mx-auto flex w-full max-w-screen-2xl gap-1 overflow-x-auto px-4 pb-2 sm:px-6", !tabs && "lg:hidden")}
            aria-label="Sections"
          >
            {links("")}
          </nav>
        )}
      </header>
      <main className={cn("flex-1 px-4 py-6 sm:px-6 lg:px-8", bottom && "pb-24 md:pb-6")}>{children}</main>
      {bottom && (
        <nav
          className="fixed inset-x-0 bottom-0 z-20 flex justify-around border-t bg-background/90 pb-[env(safe-area-inset-bottom)] backdrop-blur md:hidden"
          aria-label="Sections"
          data-proto="bottom-tabs"
        >
          {nav.map((item) => {
            const Icon = icons[item.icon];
            return (
              <Link
                key={item.href}
                href={item.href}
                data-active={active(pathname, item.href) || undefined}
                className="flex flex-1 flex-col items-center gap-0.5 py-2 text-xs text-muted-foreground data-[active]:font-semibold data-[active]:text-foreground"
              >
                {Icon && <Icon className="size-5" aria-hidden />}
                <span className="max-w-full truncate px-1">{item.label}</span>
              </Link>
            );
          })}
        </nav>
      )}
    </div>
  );
}

export function ProtoShell({ children, Kit }: { children: ReactNode; Kit: ComponentType<{ children: ReactNode }> }) {
  const proto = useProto();
  const layout = useLayout();
  const pathname = usePathname();
  const router = useRouter();
  useEffect(() => {
    const root = document.documentElement;
    root.dataset.recipe = proto.look;
    root.dataset.protoFrame = proto.on ? layout.frame : "standard";
    root.dataset.archetype = proto.on ? layout.archetype : "kit";
    root.dataset.area = layout.area?.id ?? "";
  }, [proto.look, proto.on, layout]);
  // an area whose home is its main list, in an app whose one home page is the dashboard (Story 23.10: own routes)
  useEffect(() => {
    const homePage = Object.values(app.pages).find((page) => page.route === "/");
    const dashboardHome = homePage?.sections.some((section) => section.component === "AppDashboard");
    if (!proto.on || pathname !== "/" || !dashboardHome || layout.homeView === "dashboard") return;
    const list = mainList(layout, false);
    if (list) router.replace(`${list.route}${window.location.search}`);
  }, [proto.on, pathname, layout, router]);
  if (!proto.on || layout.shell === "sidebar" || layout.shell === "rail") return <Kit>{children}</Kit>;
  return <TopBar layout={layout}>{children}</TopBar>;
}
