import type { ReactNode } from "react";
import { Grid as GridLayout } from "@/components/layout/Grid";
import { Section } from "@/components/layout/Section";
import { NESTED_SECTIONS } from "./nested";
import type { TGridContent } from "./types";

type GridProps = TGridContent & {
  children?: ReactNode;
};

/** Layout node: its child sections in a responsive grid. */
export function Grid({ title, columns = 2, gap = "md", children }: GridProps) {
  return (
    <Section title={title}>
      <GridLayout columns={columns} gap={gap} className={NESTED_SECTIONS}>
        {children}
      </GridLayout>
    </Section>
  );
}
