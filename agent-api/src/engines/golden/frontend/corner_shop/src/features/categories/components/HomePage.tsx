"use client";

import { Container } from "@/components/layout/Container";
import { CardGrid } from "@/components/sections/CardGrid";
import { Hero } from "@/components/sections/Hero";
import { QueryState } from "@/components/sections/QueryState";
import { useListCategories } from "@/lib/api/queries";

export function HomePage() {
  const categories = useListCategories({ sort: "name" });
  const items = (categories.data?.items ?? []).map((cat) => ({
    key: cat.id,
    title: cat.name,
    href: "/products",
  }));
  return (
    <div className="flex flex-col gap-8">
      <Hero
        heading="Coffee and tea, roasted down the street"
        body="Small batches, shipped the same day."
        image="asset:hero"
        cta={{ label: "Shop now", page: "products" }}
      />
      <Container className="py-8">
        <QueryState isLoading={categories.isLoading} error={categories.error} isEmpty={items.length === 0}>
          <CardGrid items={items} />
        </QueryState>
      </Container>
    </div>
  );
}
