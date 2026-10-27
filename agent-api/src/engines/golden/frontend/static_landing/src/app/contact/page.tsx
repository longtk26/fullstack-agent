import type { Metadata } from "next";
import { ContactInfo } from "@/components/sections/ContactInfo";

export const metadata: Metadata = { title: "Contact" };

export default function ContactPage() {
  return <ContactInfo email="hello@northwind.studio" phone="+44 20 7946 0000" />;
}
