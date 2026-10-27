"use client";

import { useState, type ReactNode } from "react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { ThemeProvider } from "next-themes";
import { MockGate } from "@/components/providers/MockGate";
import { Toaster } from "@/components/ui/sonner";
import { siteConfig } from "@/config/site";

type ProvidersProps = {
  children: ReactNode;
};

export function Providers({ children }: ProvidersProps) {
  const [queryClient] = useState(
    () => new QueryClient({ defaultOptions: { queries: { staleTime: 30_000, retry: 1 } } }),
  );
  return (
    <ThemeProvider
      attribute="class"
      defaultTheme={siteConfig.themeToggle ? "system" : "light"}
      enableSystem={siteConfig.themeToggle}
      disableTransitionOnChange
    >
      <QueryClientProvider client={queryClient}>
        <MockGate>{children}</MockGate>
        <Toaster richColors closeButton />
      </QueryClientProvider>
    </ThemeProvider>
  );
}
