import { Section } from "@/components/layout/Section";
import { Accordion, AccordionContent, AccordionItem, AccordionTrigger } from "@/components/ui/accordion";
import type { TFaqContent } from "./types";

type FaqProps = TFaqContent;

export function Faq({ title = "Questions", items = [] }: FaqProps) {
  return (
    <Section title={title}>
      <Accordion>
        {items.map((item) => (
          <AccordionItem key={item.question} value={item.question}>
            <AccordionTrigger>{item.question}</AccordionTrigger>
            <AccordionContent>{item.answer}</AccordionContent>
          </AccordionItem>
        ))}
      </Accordion>
    </Section>
  );
}
