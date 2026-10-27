"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import { useForm } from "react-hook-form";
import { toast } from "sonner";
import { useCreateProject } from "@/lib/api/queries";
import type { TCreateProjectRequest } from "@/lib/api/types";
import { compactValues } from "@/lib/form-utils";
import { newProjectDefaults, newProjectSchema, type TNewProjectValues } from "@/lib/forms";

/** Form `newProject` → `project.create`. */
export function useNewProjectForm() {
  const form = useForm<TNewProjectValues>({ resolver: zodResolver(newProjectSchema), defaultValues: newProjectDefaults });
  const create = useCreateProject();

  function onSubmit(values: TNewProjectValues) {
    create.mutate(compactValues(values) as TCreateProjectRequest, {
      onSuccess: () => {
        toast.success("Project created");
        form.reset(newProjectDefaults);
      },
      onError: (error) => toast.error(error.message),
    });
  }

  return { form, onSubmit, pending: create.isPending };
}
