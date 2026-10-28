"use client";

import { Container } from "@/components/layout/Container";
import { ContactInfo } from "@/components/sections/ContactInfo";
import { Form } from "@/components/sections/Form";
import { useContactForm } from "@/features/contact-messages/hooks/use-contact-form";

export function ContactPage() {
  const contact = useContactForm();
  return (
    <Container className="flex flex-col gap-8 py-8">
      <ContactInfo email="hello@corner.shop" address="1 High Street" />
      <Form
        title="Send a message"
        form={contact.form}
        onSubmit={contact.onSubmit}
        pending={contact.pending}
        submitLabel="Send"
        fields={[
          { name: "name", label: "Name", type: "string" },
          { name: "email", label: "E-mail", type: "email" },
          { name: "message", label: "Message", type: "text" },
        ]}
      />
    </Container>
  );
}
