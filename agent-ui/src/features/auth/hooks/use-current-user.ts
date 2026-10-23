"use client";

import { useQuery } from "@tanstack/react-query";
import { fetchCurrentUser } from "../api/auth-api";

export const authKeys = {
  me: ["auth", "me"] as const,
};

export function useCurrentUser() {
  return useQuery({ queryKey: authKeys.me, queryFn: fetchCurrentUser, staleTime: 5 * 60_000 });
}
