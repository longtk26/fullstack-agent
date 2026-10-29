import { Section } from "@/components/layout/Section";
import type { TRichTextContent } from "./types";

type RichTextProps = TRichTextContent;

/** Plain text: paragraphs are separated by a blank line. */
export function RichText({ heading, body }: RichTextProps) {
  return (
    <Section title={heading}>
      <div className="flex max-w-2xl flex-col gap-4 text-lg leading-relaxed">
        {body.split(/\n\s*\n/).map((paragraph) => (
          <p key={paragraph.slice(0, 40)}>{paragraph}</p>
        ))}
      </div>
    </Section>
  );
}
