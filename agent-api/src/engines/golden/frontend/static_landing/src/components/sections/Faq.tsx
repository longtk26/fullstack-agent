import { Section } from "@/components/layout/Section";
import { Accordion, AccordionContent, AccordionItem, AccordionTrigger } from "@/components/ui/accordion";

export type TQuestion = { question: string; answer: string };

type FaqProps = {
  items: TQuestion[];
};

export function Faq({ items }: FaqProps) {
  return (
    <Section title="Questions">
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
