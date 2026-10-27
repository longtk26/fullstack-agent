import { Suspense } from "react";
import { Skeleton } from "@/components/ui/skeleton";
import { Container } from "@/components/layout/Container";
import { Stack } from "@/components/layout/Stack";
import { UsageView } from "@/features/usage/components/UsageView";

export default function UsagePage() {
  return (
    <Container size="xl">
      <Stack gap="lg">
        <Stack gap="xs">
          <h1 className="text-2xl font-semibold tracking-tight">Usage & traces</h1>
          <p className="text-sm text-muted-foreground">
            Time, model calls, tokens and cost of your generations, and where they went.
          </p>
        </Stack>
        <Suspense fallback={<Skeleton className="h-[600px] w-full" />}>
          <UsageView />
        </Suspense>
      </Stack>
    </Container>
  );
}
