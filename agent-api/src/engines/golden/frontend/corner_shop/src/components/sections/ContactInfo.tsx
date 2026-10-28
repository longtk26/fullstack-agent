import { Mail, MapPin, Phone } from "lucide-react";
import { Section } from "@/components/layout/Section";
import { Card, CardContent } from "@/components/ui/card";

type ContactInfoProps = {
  email?: string;
  phone?: string;
  address?: string;
};

export function ContactInfo({ email, phone, address }: ContactInfoProps) {
  return (
    <Section title="Get in touch">
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
              <MapPin className="size-4" aria-hidden /> {address}
            </p>
          )}
        </CardContent>
      </Card>
    </Section>
  );
}
