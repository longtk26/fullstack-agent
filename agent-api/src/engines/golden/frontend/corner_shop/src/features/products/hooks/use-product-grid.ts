"use client";

import { useListProducts } from "@/lib/api/queries";

export function useProductGrid(limit = 12) {
  const query = useListProducts({ limit, sort: "-createdAt" });
  return {
    products: query.data?.items ?? [],
    isLoading: query.isLoading,
    error: query.error,
  };
}
