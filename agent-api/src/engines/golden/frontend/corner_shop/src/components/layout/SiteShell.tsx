import type { ReactNode } from "react";
import Link from "next/link";
import { Container } from "@/components/layout/Container";
import { ThemeToggle } from "@/components/layout/ThemeToggle";
import { siteConfig } from "@/config/site";
import { MobileNav } from "./MobileNav";

type SiteShellProps = {
  children: ReactNode;
};

/** Header (logo + navigation), the page, footer: FrontendSpec.layout `header-footer`. */
export function SiteShell({ children }: SiteShellProps) {
  return (
    <div className="flex min-h-dvh flex-col">
      <header className="sticky top-0 z-40 border-b bg-background/90 backdrop-blur">
        <Container className="flex h-16 items-center justify-between gap-4">
          <Link href="/" className="font-heading text-lg font-semibold tracking-tight">
            {siteConfig.logoText}
          </Link>
          <div className="flex items-center gap-2">
            <nav aria-label="Main" className="hidden items-center gap-1 md:flex">
              {siteConfig.navigation.map((item) => (
                <Link
                  key={item.href}
                  href={item.href}
                  className="rounded-md px-3 py-2 text-sm text-muted-foreground transition-colors hover:bg-muted hover:text-foreground"
                >
                  {item.label}
                </Link>
              ))}
            </nav>
            {siteConfig.themeToggle && <ThemeToggle />}
            <MobileNav />
          </div>
        </Container>
      </header>
      <main className="flex-1">{children}</main>
      <footer className="border-t bg-muted/40">
        <Container className="flex flex-col gap-3 py-8 text-sm text-muted-foreground sm:flex-row sm:items-center sm:justify-between">
          <p>{siteConfig.footer.text}</p>
          <nav aria-label="Footer" className="flex gap-4">
            {siteConfig.footer.links.map((item) =>
              "external" in item ? (
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
