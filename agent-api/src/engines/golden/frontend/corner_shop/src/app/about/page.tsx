import type { Metadata } from "next";
import { Hero } from "@/components/sections/Hero";
import { Testimonials } from "@/components/sections/Testimonials";
import testimonials from "@/content/testimonials.json";

export const metadata: Metadata = { title: "About" };

export default function Page() {
  return (
    <div className="flex flex-col gap-8">
      <Hero heading="Our story" body="Two friends, one roaster." image="asset:shop-front" />
      <Testimonials items={testimonials} />
    </div>
  );
}
