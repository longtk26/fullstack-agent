import type { ReactNode } from "react";
import type { Metadata } from "next";
import { SiteShell } from "@/components/layout/SiteShell";
import { siteConfig } from "@/config/site";
import { Providers } from "./providers";
import "./globals.css";

export const metadata: Metadata = {
  title: { default: siteConfig.name, template: `%s | ${siteConfig.name}` },
  description: siteConfig.description,
};

type RootLayoutProps = {
  children: ReactNode;
};

export default function RootLayout({ children }: RootLayoutProps) {
  return (
    <html lang={siteConfig.locale} suppressHydrationWarning>
      <body className="min-h-dvh bg-background text-foreground antialiased">
        <Providers>
          <SiteShell>{children}</SiteShell>
        </Providers>
      </body>
    </html>
  );
}
