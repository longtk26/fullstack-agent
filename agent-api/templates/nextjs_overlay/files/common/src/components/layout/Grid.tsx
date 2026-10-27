import type { ComponentProps } from "react";
import { cn } from "@/lib/utils";

type GridProps = ComponentProps<"div"> & {
  columns?: 1 | 2 | 3 | 4;
  gap?: "sm" | "md" | "lg";
};

const COLUMNS = {
  1: "grid-cols-1",
  2: "grid-cols-1 sm:grid-cols-2",
  3: "grid-cols-1 sm:grid-cols-2 lg:grid-cols-3",
  4: "grid-cols-1 sm:grid-cols-2 lg:grid-cols-4",
} as const;
const GAPS = { sm: "gap-3", md: "gap-6", lg: "gap-8" } as const;

/** Responsive grid: one column on phones, `columns` on wide screens. */
export function Grid({ columns = 3, gap = "md", className, ...props }: GridProps) {
  return <div className={cn("grid", COLUMNS[columns], GAPS[gap], className)} {...props} />;
}
