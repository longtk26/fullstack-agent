import type { TUsageScope } from "./types";

export const usageKeys = {
  all: ["usage"] as const,
  report: (from: string, to: string, scope: TUsageScope) => [...usageKeys.all, "report", from, to, scope] as const,
};
