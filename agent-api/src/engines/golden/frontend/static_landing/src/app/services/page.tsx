import type { Metadata } from "next";
import { Faq } from "@/components/sections/Faq";
import { Features } from "@/components/sections/Features";
import { Pricing } from "@/components/sections/Pricing";
import faq from "@/content/faq.json";
import plans from "@/content/plans.json";
import services from "@/content/services.json";

export const metadata: Metadata = { title: "Services" };

export default function ServicesPage() {
  return (
    <>
      <Features title="Services" items={services} />
      <Pricing plans={plans} />
      <Faq items={faq} />
    </>
  );
}
