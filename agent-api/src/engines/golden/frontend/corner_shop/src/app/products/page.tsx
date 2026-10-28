import type { Metadata } from "next";
import { Container } from "@/components/layout/Container";
import { ProductGrid } from "@/features/products/components/ProductGrid";

export const metadata: Metadata = {
  title: "Shop all products",
  description: "Coffee, tea and brewing gear",
};

export default function Page() {
  return (
    <Container className="flex flex-col gap-6 py-8">
      <h1 className="text-2xl font-semibold tracking-tight">Products</h1>
      <ProductGrid />
    </Container>
  );
}
