import { Children, type ReactNode } from "react";
import { Section } from "@/components/layout/Section";
import { Tabs as TabsRoot, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { NESTED_SECTIONS } from "./nested";
import type { TTabsContent } from "./types";

type TabsProps = TTabsContent & {
  children?: ReactNode;
  childTitles?: string[];
};

/** Layout node: one tab per child section, labelled by `labels` or the child's title. */
export function Tabs({ labels, children, childTitles = [] }: TabsProps) {
  const panels = Children.toArray(children);
  const names = labels ?? childTitles;
  return (
    <Section>
      <TabsRoot defaultValue={0}>
        <TabsList>
          {panels.map((_, index) => (
            <TabsTrigger key={names[index] ?? index} value={index}>
              {names[index] ?? `Tab ${index + 1}`}
            </TabsTrigger>
          ))}
        </TabsList>
        {panels.map((panel, index) => (
          <TabsContent key={names[index] ?? index} value={index} className={NESTED_SECTIONS}>
            {panel}
          </TabsContent>
        ))}
      </TabsRoot>
    </Section>
  );
}
