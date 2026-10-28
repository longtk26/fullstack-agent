import type { Metadata } from "next";
import { ProductDetailPage } from "@/features/products/components/ProductDetailPage";

export const metadata: Metadata = { title: "Product" };

type PageProps = {
  params: Promise<{ id: string }>;
};

export default async function Page({ params }: PageProps) {
  const { id } = await params;
  return <ProductDetailPage id={id} />;
}
