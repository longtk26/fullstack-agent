"use client";

import { useState } from "react";
import { Ban } from "lucide-react";
import { toast } from "sonner";
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
  AlertDialogTrigger,
} from "@/components/ui/alert-dialog";
import { Button } from "@/components/ui/button";
import { useCancelGeneration } from "../../hooks/use-generation-mutations";

type CancelGenerationButtonProps = {
  generationId: string;
  disabled: boolean;
  cancelRequested: boolean;
};

export function CancelGenerationButton({ generationId, disabled, cancelRequested }: CancelGenerationButtonProps) {
  const cancel = useCancelGeneration(generationId);
  const [open, setOpen] = useState(false);

  return (
    <AlertDialog open={open} onOpenChange={setOpen}>
      <AlertDialogTrigger
        render={<Button variant="outline" size="sm" disabled={disabled || cancelRequested || cancel.isPending} />}
      >
        <Ban /> {cancelRequested ? "Cancelling…" : "Cancel"}
      </AlertDialogTrigger>
      <AlertDialogContent>
        <AlertDialogHeader>
          <AlertDialogTitle>Cancel this generation?</AlertDialogTitle>
          <AlertDialogDescription>
            The engine is stopped and the job ends as CANCELLED. Files written so far stay in the workspace.
          </AlertDialogDescription>
        </AlertDialogHeader>
        <AlertDialogFooter>
          <AlertDialogCancel>Keep running</AlertDialogCancel>
          <AlertDialogAction
            variant="destructive"
            onClick={() => {
              setOpen(false);
              cancel.mutate(undefined, {
                onError: (error) => toast.error(error.message),
                onSuccess: () => toast.success("Cancel requested"),
              });
            }}
          >
            Cancel generation
          </AlertDialogAction>
        </AlertDialogFooter>
      </AlertDialogContent>
    </AlertDialog>
  );
}
