import type { ReactNode } from "react";
import { Section } from "@/components/layout/Section";
import { Stack as StackLayout } from "@/components/layout/Stack";
import { NESTED_SECTIONS } from "./nested";
import type { TStackContent } from "./types";

type StackProps = TStackContent & {
  children?: ReactNode;
};

const GAPS = { sm: "sm", md: "lg", lg: "xl" } as const;

/** Layout node: its child sections one under another. */
export function Stack({ title, gap = "md", children }: StackProps) {
  return (
    <Section title={title}>
      <StackLayout gap={GAPS[gap]} className={NESTED_SECTIONS}>
        {children}
      </StackLayout>
    </Section>
  );
}
