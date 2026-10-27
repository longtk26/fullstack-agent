import { apiClient } from "@/lib/api-client";
import type { TUsageReport, TUsageScope } from "../types";

export function fetchUsage(from: string, to: string, scope: TUsageScope) {
  return apiClient.get<TUsageReport>("/usage", { query: { from, to, scope } });
}
