import { apiClient } from "@/lib/api-client";
import type { TCurrentUser } from "@/types/auth";

export function fetchCurrentUser() {
  return apiClient.get<TCurrentUser>("/me");
}
