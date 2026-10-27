import type { ComponentProps } from "react";
import { cn } from "@/lib/utils";

type ContainerProps = ComponentProps<"div"> & {
  size?: "sm" | "md" | "lg" | "xl";
};

const SIZES = { sm: "max-w-2xl", md: "max-w-4xl", lg: "max-w-6xl", xl: "max-w-7xl" } as const;

/** Centered page-width wrapper with the horizontal gutter. */
export function Container({ size = "lg", className, ...props }: ContainerProps) {
  return <div className={cn("mx-auto w-full px-4 sm:px-6", SIZES[size], className)} {...props} />;
}
