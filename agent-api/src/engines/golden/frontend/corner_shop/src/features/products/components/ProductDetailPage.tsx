"use client";

import { Container } from "@/components/layout/Container";
import { Form } from "@/components/sections/Form";
import { useAddToCartForm } from "@/features/cart-items/hooks/use-add-to-cart-form";
import { ProductDetail } from "@/features/products/components/ProductDetail";

type ProductDetailPageProps = {
  id: string;
};

export function ProductDetailPage({ id }: ProductDetailPageProps) {
  const addToCart = useAddToCartForm(id);
  return (
    <Container className="flex flex-col gap-8 py-8">
      <ProductDetail id={id} />
      <Form
        title="Add to cart"
        form={addToCart.form}
        onSubmit={addToCart.onSubmit}
        pending={addToCart.pending}
        submitLabel="Add to cart"
        fields={[{ name: "quantity", label: "Quantity", type: "integer" }]}
      />
    </Container>
  );
}
