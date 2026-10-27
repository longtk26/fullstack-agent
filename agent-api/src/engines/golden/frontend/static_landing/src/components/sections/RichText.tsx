import { Section } from "@/components/layout/Section";

type RichTextProps = {
  body: string;
};

export function RichText({ body }: RichTextProps) {
  return (
    <Section>
      <p className="max-w-2xl text-lg leading-relaxed">{body}</p>
    </Section>
  );
}
