import { Mail, MapPin, Phone } from "lucide-react";
import { Section } from "@/components/layout/Section";
import { Card, CardContent } from "@/components/ui/card";
import type { TContactInfoContent } from "./types";

type ContactInfoProps = TContactInfoContent;

export function ContactInfo({ title = "Get in touch", email, phone, address, mapUrl }: ContactInfoProps) {
  return (
    <Section title={title}>
      <Card className="max-w-md">
        <CardContent className="flex flex-col gap-3">
          {email && (
            <a href={`mailto:${email}`} className="flex items-center gap-2 hover:text-primary">
              <Mail className="size-4" aria-hidden /> {email}
            </a>
          )}
          {phone && (
            <a href={`tel:${phone.replaceAll(" ", "")}`} className="flex items-center gap-2 hover:text-primary">
              <Phone className="size-4" aria-hidden /> {phone}
            </a>
          )}
          {address && (
            <p className="flex items-center gap-2">
              <MapPin className="size-4" aria-hidden />
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
