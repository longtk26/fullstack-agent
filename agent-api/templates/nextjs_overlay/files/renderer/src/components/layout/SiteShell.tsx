import type { ReactNode } from "react";
import Link from "next/link";
import { Container } from "@/components/layout/Container";
import { ThemeToggle } from "@/components/layout/ThemeToggle";
import { siteConfig, type TNavItem } from "@/config/site";
import { MobileNav } from "./MobileNav";

type SiteShellProps = {
  children: ReactNode;
};

/** FrontendSpec.layout: `header-footer` (logo, navigation, footer) or `blank` (the page only). */
// `siteConfig` is `as const`, so its values are per-site literals; widen them before branching on them.
const shell: string = siteConfig.shell;
const navigation: readonly TNavItem[] = siteConfig.navigation;
const footerLinks: readonly TNavItem[] = siteConfig.footer.links;

export function SiteShell({ children }: SiteShellProps) {
  if (shell === "blank") {
    return <main className="flex min-h-dvh flex-col">{children}</main>;
  }
  return (
    <div className="flex min-h-dvh flex-col">
      <header className="sticky top-0 z-40 border-b bg-background/90 backdrop-blur">
        <Container className="flex h-16 items-center justify-between gap-4">
          <Link href="/" className="font-heading text-lg font-semibold tracking-tight">
            {siteConfig.logoText}
          </Link>
          <div className="flex items-center gap-1">
            <nav aria-label="Main" className="hidden items-center gap-1 md:flex">
              {navigation.map((item) => (
                <Link
                  key={item.href}
                  href={item.href}
                  className="rounded-md px-3 py-2 text-sm text-muted-foreground hover:bg-muted hover:text-foreground"
                >
                  {item.label}
                </Link>
              ))}
            </nav>
            {siteConfig.themeToggle && <ThemeToggle />}
            {navigation.length > 0 && <MobileNav />}
          </div>
        </Container>
      </header>
      <main className="flex-1">{children}</main>
      <footer className="border-t bg-muted/40">
        <Container className="flex flex-col gap-3 py-8 text-sm text-muted-foreground sm:flex-row sm:items-center sm:justify-between">
          <p>{siteConfig.footer.text}</p>
          <nav aria-label="Footer" className="flex gap-4">
            {footerLinks.map((item) =>
              item.external ? (
                <a key={item.href} href={item.href} className="hover:text-foreground" rel="noreferrer" target="_blank">
                  {item.label}
                </a>
              ) : (
                <Link key={item.href} href={item.href} className="hover:text-foreground">
                  {item.label}
                </Link>
              ),
            )}
          </nav>
        </Container>
      </footer>
    </div>
  );
}
