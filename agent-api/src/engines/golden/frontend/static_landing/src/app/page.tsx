import type { Metadata } from "next";
import { CallToAction } from "@/components/sections/CallToAction";
import { Features } from "@/components/sections/Features";
import { Hero } from "@/components/sections/Hero";
import { Testimonials } from "@/components/sections/Testimonials";
import services from "@/content/services.json";
import testimonials from "@/content/testimonials.json";

export const metadata: Metadata = {
  title: "Home",
  description: "Brand and web design for independent businesses",
};

export default function HomePage() {
  return (
    <>
      <Hero
        heading="Design that sounds like you"
        body="Brand and web design for independent businesses."
        image="asset:hero"
        cta={{ label: "See our work", page: "work" }}
      />
      <Features items={services} />
      <Testimonials items={testimonials} />
      <CallToAction heading="Have a project?" cta={{ label: "Get in touch", page: "contact" }} />
    </>
  );
}
