import type { ReactNode } from "react";
import { AlertCircle } from "lucide-react";
import { Skeleton } from "@/components/ui/skeleton";

type QueryStateProps = {
  isLoading: boolean;
  error: Error | null;
  isEmpty: boolean;
  emptyText?: string;
  errorText?: string;
  children: ReactNode;
};

/** The loading, error and empty states every data section shows (FrontendSpec `states`). */
export function QueryState({ isLoading, error, isEmpty, emptyText, errorText, children }: QueryStateProps) {
  if (isLoading) {
    return (
      <div className="flex flex-col gap-2" aria-busy="true">
        <Skeleton className="h-8 w-full" />
        <Skeleton className="h-8 w-full" />
        <Skeleton className="h-8 w-2/3" />
      </div>
    );
  }
  if (error) {
    return (
      <p role="alert" className="flex items-center gap-2 text-destructive">
        <AlertCircle className="size-4" aria-hidden /> {errorText ?? error.message}
      </p>
    );
  }
  if (isEmpty) return <p className="text-muted-foreground">{emptyText ?? "Nothing here yet"}</p>;
  return children;
}
