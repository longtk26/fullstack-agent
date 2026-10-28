"use client";

import { useDeleteCartItem, useListCartItems } from "@/lib/api/queries";

export function useCartList() {
  const query = useListCartItems({ sort: "createdAt" });
  const remove = useDeleteCartItem();
  return {
    items: query.data?.items ?? [],
    isLoading: query.isLoading,
    error: query.error,
    removeItem: (id: string) => remove.mutate({ id }),
  };
}
