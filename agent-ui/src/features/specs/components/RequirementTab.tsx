import { Info } from "lucide-react";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { Stack } from "@/components/layout/Stack";

const EXAMPLE_PROMPTS = [
  "A task tracker: projects have many tasks; tasks have a title, status (todo, doing, done), due date and assignee email.",
  "A small library: books, authors and loans. Members borrow books for 14 days; list overdue loans.",
];

export function RequirementTab() {
  return (
    <Stack gap="md">
      <Alert>
        <Info />
        <AlertTitle>Requirement drafting is not available yet</AlertTitle>
        <AlertDescription>
          Turning plain language into a BackendSpec arrives with Story 2.4. For now, use the Import or JSON tab.
        </AlertDescription>
      </Alert>
      <Textarea rows={8} disabled placeholder={EXAMPLE_PROMPTS[0]} />
      <Stack direction="row" gap="xs" wrap>
        {EXAMPLE_PROMPTS.map((prompt) => (
          <Button key={prompt} variant="outline" size="sm" disabled className="max-w-full truncate">
            {prompt.split(":")[0]}
          </Button>
        ))}
      </Stack>
      <div>
        <Button disabled>Draft spec</Button>
      </div>
    </Stack>
  );
}
