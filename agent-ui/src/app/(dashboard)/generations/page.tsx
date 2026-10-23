import Link from "next/link";
import { Plus } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Container } from "@/components/layout/Container";
import { Stack } from "@/components/layout/Stack";
import { GenerationsList } from "@/features/generations/components/GenerationsList";

export default function GenerationsPage() {
  return (
    <Container>
      <Stack gap="lg">
        <Stack direction="row" justify="between" align="center">
          <Stack gap="xs">
            <h1 className="text-2xl font-semibold tracking-tight">Generations</h1>
            <p className="text-sm text-muted-foreground">Every backend you generated, newest first.</p>
          </Stack>
          <Button render={<Link href="/generations/new" />} nativeButton={false}>
            <Plus /> New generation
          </Button>
        </Stack>
        <GenerationsList />
      </Stack>
    </Container>
  );
}
