import type { Metadata } from "next";
import { RichText } from "@/components/sections/RichText";
import { Stats } from "@/components/sections/Stats";

export const metadata: Metadata = { title: "About" };

export default function AboutPage() {
  return (
    <>
      <RichText body="Northwind is a two-person studio. We have helped forty small businesses find their voice since 2019." />
      <Stats
        items={[
          { label: "Clients", value: "40+" },
          { label: "Years", value: "6" },
        ]}
      />
    </>
  );
}
