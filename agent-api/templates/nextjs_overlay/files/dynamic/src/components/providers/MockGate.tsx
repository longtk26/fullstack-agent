"use client";

import { useEffect, useState, type ReactNode } from "react";
import { loadRuntimeConfig } from "@/lib/runtime-config";

type MockGateProps = {
  children: ReactNode;
};

/** Starts the mock API (MSW) before anything fetches, when the server says `MOCK_TEST_API=true`. */
export function MockGate({ children }: MockGateProps) {
  const [ready, setReady] = useState(false);

  useEffect(() => {
    let active = true;
    loadRuntimeConfig()
      .then(async (config) => {
        if (!config.mockApi) return;
        const { worker } = await import("@/mocks/browser");
        await worker.start({ onUnhandledRequest: "bypass", quiet: true });
      })
      .finally(() => {
        if (active) setReady(true);
      });
    return () => {
      active = false;
    };
  }, []);

  return ready ? children : null;
}
