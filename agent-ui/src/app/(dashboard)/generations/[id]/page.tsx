import { Suspense } from "react";
import { Container } from "@/components/layout/Container";
import {
  GenerationDetailSkeleton,
  GenerationDetailView,
} from "@/features/generations/components/detail/GenerationDetailView";

async function GenerationDetail({ params }: Pick<PageProps<"/generations/[id]">, "params">) {
  const { id } = await params;
  return <GenerationDetailView id={id} />;
}

export default function GenerationDetailPage({ params }: PageProps<"/generations/[id]">) {
  return (
    <Container size="xl">
      <Suspense fallback={<GenerationDetailSkeleton />}>
        <GenerationDetail params={params} />
      </Suspense>
    </Container>
  );
}
