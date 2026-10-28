import type { Metadata } from "next";
import { Container } from "@/components/layout/Container";
import { CartList } from "@/features/cart-items/components/CartList";

export const metadata: Metadata = { title: "Cart" };

export default function Page() {
  return (
    <Container className="flex flex-col gap-6 py-8">
      <h1 className="text-2xl font-semibold tracking-tight">Cart</h1>
      <CartList />
    </Container>
  );
}
