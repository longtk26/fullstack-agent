import { Section } from "@/components/layout/Section";
import { Card, CardContent } from "@/components/ui/card";
import { backdropImage } from "./AssetImage";
import { Icon } from "./Icon";
import type { TContactInfoContent } from "./types";

type ContactInfoProps = TContactInfoContent;

export function ContactInfo(props: ContactInfoProps) {
  const { title = "Get in touch", email, phone, address, mapUrl, background, backgroundImage } = props;
  return (
    <Section title={title} background={background} backdrop={backdropImage(backgroundImage)}>
      <Card className="max-w-md">
        <CardContent className="flex flex-col gap-3">
          {email && (
            <a href={`mailto:${email}`} className="flex items-center gap-2 hover:text-primary">
              <Icon glyph="mail" decorative className="size-4" /> {email}
            </a>
          )}
          {phone && (
            <a href={`tel:${phone.replaceAll(" ", "")}`} className="flex items-center gap-2 hover:text-primary">
              <Icon glyph="phone" decorative className="size-4" /> {phone}
            </a>
          )}
          {address && (
            <p className="flex items-center gap-2">
              <Icon glyph="mapPin" decorative className="size-4" />
              {mapUrl ? (
                <a href={mapUrl} className="hover:text-primary" rel="noreferrer" target="_blank">
                  {address}
                </a>
              ) : (
                address
              )}
            </p>
          )}
        </CardContent>
      </Card>
    </Section>
  );
}
