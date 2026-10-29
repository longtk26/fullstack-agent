import type { ReactNode } from "react";
import { Grid as GridLayout } from "@/components/layout/Grid";
import { Section } from "@/components/layout/Section";
import { NESTED_SECTIONS } from "./nested";
import type { TColumnsContent } from "./types";

type ColumnsProps = TColumnsContent & {
  children?: ReactNode;
  childTitles?: string[];
};

/** Layout node: its child sections side by side (one column per child, at most four). */
export function Columns({ title, columns, gap = "md", children, childTitles = [] }: ColumnsProps) {
  const count = columns ?? (Math.min(Math.max(childTitles.length, 1), 4) as 1 | 2 | 3 | 4);
  return (
    <Section title={title}>
      <GridLayout columns={count} gap={gap} className={NESTED_SECTIONS}>
        {children}
      </GridLayout>
    </Section>
  );
}
