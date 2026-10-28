"use client";

import { useGetProduct } from "@/lib/api/queries";

export function useProductDetail(id: string) {
  const query = useGetProduct({ id });
  return {
    product: query.data ?? null,
    isLoading: query.isLoading,
    error: query.error,
  };
}
