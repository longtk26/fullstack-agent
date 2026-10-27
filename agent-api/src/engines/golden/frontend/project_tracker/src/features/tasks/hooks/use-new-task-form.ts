"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import { useForm } from "react-hook-form";
import { toast } from "sonner";
import { useCreateTask } from "@/lib/api/queries";
import type { TCreateTaskRequest } from "@/lib/api/types";
import { compactValues } from "@/lib/form-utils";
import { newTaskDefaults, newTaskSchema, type TNewTaskValues } from "@/lib/forms";

/** Form `newTask` → `task.create`; `projectId` comes from the route. */
export function useNewTaskForm(projectId: string) {
  const defaults = { ...newTaskDefaults, projectId };
  const form = useForm<TNewTaskValues>({ resolver: zodResolver(newTaskSchema), defaultValues: defaults });
  const create = useCreateTask();

  function onSubmit(values: TNewTaskValues) {
    create.mutate(compactValues(values) as TCreateTaskRequest, {
      onSuccess: () => {
        toast.success("Task added");
        form.reset(defaults);
      },
      onError: (error) => toast.error(error.message),
    });
  }

  return { form, onSubmit, pending: create.isPending };
}
