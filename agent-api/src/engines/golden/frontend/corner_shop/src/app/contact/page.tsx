import type { Metadata } from "next";
import { ContactPage } from "@/features/contact-messages/components/ContactPage";

export const metadata: Metadata = { title: "Contact" };

export default function Page() {
  return <ContactPage />;
}
