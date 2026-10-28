"use client";

import { useRouter } from "next/navigation";
import { zodResolver } from "@hookform/resolvers/zod";
import { useForm } from "react-hook-form";
import { toast } from "sonner";
import { useCreateCartItem } from "@/lib/api/queries";
import { addToCartDefaults, addToCartSchema, type TAddToCartValues } from "@/lib/forms";

/** Form `addToCart` → `cartItem.create`. */
export function useAddToCartForm(productId: string) {
  const router = useRouter();
  const defaults: TAddToCartValues = { productId, quantity: addToCartDefaults.quantity ?? 1 };
  const form = useForm<TAddToCartValues>({ resolver: zodResolver(addToCartSchema), defaultValues: defaults });
  const create = useCreateCartItem();

  function onSubmit(values: TAddToCartValues) {
    create.mutate(
      { productId, quantity: values.quantity },
      {
        onSuccess: () => {
          toast.success("Added to cart");
          router.push("/cart");
        },
        onError: (error) => toast.error(error.message),
      },
    );
  }

  return { form, onSubmit, pending: create.isPending };
}
