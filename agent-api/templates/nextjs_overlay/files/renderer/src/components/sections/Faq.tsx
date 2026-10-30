import { Section } from "@/components/layout/Section";
import { Accordion, AccordionContent, AccordionItem, AccordionTrigger } from "@/components/ui/accordion";
import { backdropImage } from "./AssetImage";
import type { TFaqContent } from "./types";

type FaqProps = TFaqContent;

export function Faq({ title = "Questions", items = [], background, backgroundImage }: FaqProps) {
  return (
    <Section title={title} background={background} backdrop={backdropImage(backgroundImage)}>
      <Accordion className="max-w-3xl">
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
