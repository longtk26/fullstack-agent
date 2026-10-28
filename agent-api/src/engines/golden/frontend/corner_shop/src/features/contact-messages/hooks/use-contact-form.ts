"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import { useForm } from "react-hook-form";
import { toast } from "sonner";
import { useCreateContactMessage } from "@/lib/api/queries";
import { contactDefaults, contactSchema, type TContactValues } from "@/lib/forms";

/** Form `contact` → `contactMessage.create`. */
export function useContactForm() {
  const form = useForm<TContactValues>({ resolver: zodResolver(contactSchema), defaultValues: contactDefaults });
  const create = useCreateContactMessage();

  function onSubmit(values: TContactValues) {
    create.mutate(values, {
      onSuccess: () => {
        toast.success("Thanks, we will get back to you");
        form.reset(contactDefaults);
      },
      onError: (error) => toast.error(error.message),
    });
  }

  return { form, onSubmit, pending: create.isPending };
}
