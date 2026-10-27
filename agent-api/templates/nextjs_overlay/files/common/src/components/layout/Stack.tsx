import type { ComponentProps } from "react";
import { cn } from "@/lib/utils";

type StackProps = ComponentProps<"div"> & {
  direction?: "row" | "column";
  gap?: "xs" | "sm" | "md" | "lg" | "xl";
  align?: "start" | "center" | "end" | "stretch";
  justify?: "start" | "center" | "end" | "between";
  wrap?: boolean;
};

const GAPS = { xs: "gap-1", sm: "gap-2", md: "gap-4", lg: "gap-6", xl: "gap-10" } as const;
const ALIGN = { start: "items-start", center: "items-center", end: "items-end", stretch: "items-stretch" } as const;
const JUSTIFY = { start: "justify-start", center: "justify-center", end: "justify-end", between: "justify-between" } as const;

/** Flex row or column with token spacing. */
export function Stack({ direction = "column", gap = "md", align, justify, wrap, className, ...props }: StackProps) {
  return (
    <div
      className={cn(
        "flex",
        direction === "row" ? "flex-row" : "flex-col",
        GAPS[gap],
        align && ALIGN[align],
        justify && JUSTIFY[justify],
        wrap && "flex-wrap",
        className,
      )}
      {...props}
    />
  );
}
