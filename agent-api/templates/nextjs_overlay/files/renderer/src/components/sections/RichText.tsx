import { Section } from "@/components/layout/Section";
import { backdropImage } from "./AssetImage";
import type { TRichTextContent } from "./types";

type RichTextProps = TRichTextContent;

/** Plain text: paragraphs are separated by a blank line. */
export function RichText({ heading, body, background, backgroundImage }: RichTextProps) {
  return (
    <Section title={heading} background={background} backdrop={backdropImage(backgroundImage)}>
      <div className="flex max-w-prose flex-col gap-4 text-lg leading-relaxed">
        {body.split(/\n\s*\n/).map((paragraph) => (
          <p key={paragraph.slice(0, 40)}>{paragraph}</p>
        ))}
      </div>
    </Section>
  );
}
