"use client";

import { Controller } from "react-hook-form";
import type { UseFormReturn } from "react-hook-form";
import {
  Field,
  FieldContent,
  FieldDescription,
  FieldError,
  FieldGroup,
  FieldLabel,
  FieldLegend,
  FieldSet,
} from "@/components/ui/field";
import { Input } from "@/components/ui/input";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Switch } from "@/components/ui/switch";
import type { TEngineInfo } from "@/features/specs/types";
import type { TGenerationOptionsFormValues } from "../schemas/generation-options-schema";
import type { TGenerationMode } from "../types";

const ENGINE_LABELS: Record<string, string> = {
  claude_code: "Claude Code",
  antigravity: "Antigravity",
  fake: "Fake (test/demo: bundled examples only)",
};

type TToggle = {
  name: "runTests" | "generateDockerfile" | "deployPreview" | "frontend.runTests" | "frontend.generatePreview" | "frontend.mockApi";
  label: string;
  description: string;
};

const BACKEND_TOGGLES: TToggle[] = [
  { name: "runTests", label: "Run tests", description: "Generate and run pytest in the sandbox" },
  { name: "generateDockerfile", label: "Generate Dockerfile", description: "Package the backend as an image" },
  { name: "deployPreview", label: "Deploy preview", description: "Start a container clients can call" },
];

const FRONTEND_TOGGLES: TToggle[] = [
  { name: "frontend.runTests", label: "Run tests", description: "Build, lint and test the site in the sandbox" },
  { name: "frontend.generatePreview", label: "Preview site", description: "Start a container to open the site" },
];

const MOCK_API_TOGGLE: TToggle = {
  name: "frontend.mockApi",
  label: "Mock API",
  description: "The site calls mocks generated from the API contract",
};

/** Toggle groups per mode; the heading is shown only when both lanes have options. */
function toggleGroups(mode: TGenerationMode): { heading: string | null; toggles: TToggle[] }[] {
  if (mode === "backend") return [{ heading: null, toggles: BACKEND_TOGGLES }];
  if (mode === "static") return [{ heading: null, toggles: FRONTEND_TOGGLES }];
  return [
    { heading: "Backend", toggles: BACKEND_TOGGLES },
    { heading: "Frontend", toggles: [...FRONTEND_TOGGLES, MOCK_API_TOGGLE] },
  ];
}

type GenerationOptionsFormProps = {
  form: UseFormReturn<TGenerationOptionsFormValues>;
  engines: TEngineInfo[];
  mode: TGenerationMode;
};

export function GenerationOptionsForm({ form, engines, mode }: GenerationOptionsFormProps) {
  const engineItems = engines.map((engine) => ({ value: engine.name, label: ENGINE_LABELS[engine.name] ?? engine.name }));

  return (
    <FieldGroup>
      <Controller
        name="engine"
        control={form.control}
        render={({ field, fieldState }) => (
          <Field data-invalid={fieldState.invalid}>
            <FieldLabel htmlFor="engine">Engine</FieldLabel>
            <Select items={engineItems} value={field.value} onValueChange={(value) => field.onChange(value)}>
              <SelectTrigger id="engine" className="w-full">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {engines.map((engine) => (
                  <SelectItem key={engine.name} value={engine.name} disabled={!engine.available}>
                    {ENGINE_LABELS[engine.name] ?? engine.name}
                    {!engine.available && <span className="text-xs text-muted-foreground">unavailable</span>}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
            {engines.find((engine) => engine.name === field.value && !engine.available)?.reason && (
              <FieldDescription>
                {engines.find((engine) => engine.name === field.value)?.reason}
              </FieldDescription>
            )}
            <FieldError errors={[fieldState.error]} />
          </Field>
        )}
      />
      <Controller
        name="maxRepairAttempts"
        control={form.control}
        render={({ field, fieldState }) => (
          <Field data-invalid={fieldState.invalid}>
            <FieldLabel htmlFor="maxRepairAttempts">Max repair attempts</FieldLabel>
            <Input
              id="maxRepairAttempts"
              type="number"
              min={1}
              max={10}
              value={Number.isNaN(field.value) ? "" : field.value}
              onChange={(event) => field.onChange(event.target.valueAsNumber)}
              onBlur={field.onBlur}
              aria-invalid={fieldState.invalid}
            />
            <FieldError errors={[fieldState.error]} />
          </Field>
        )}
      />
      {toggleGroups(mode).map((group) => (
        <FieldSet key={group.heading ?? "options"}>
          {group.heading && <FieldLegend variant="label">{group.heading}</FieldLegend>}
          {group.toggles.map((toggle) => (
            <Controller
              key={toggle.name}
              name={toggle.name}
              control={form.control}
              render={({ field, fieldState }) => (
                <Field orientation="horizontal" data-invalid={fieldState.invalid}>
                  <FieldContent>
                    <FieldLabel htmlFor={toggle.name}>{toggle.label}</FieldLabel>
                    <FieldDescription>{toggle.description}</FieldDescription>
                    <FieldError errors={[fieldState.error]} />
                  </FieldContent>
                  <Switch
                    id={toggle.name}
                    checked={field.value}
                    onCheckedChange={(checked) => {
                      field.onChange(checked);
                      form.trigger(["deployPreview"]);
                    }}
                  />
                </Field>
              )}
            />
          ))}
        </FieldSet>
      ))}
    </FieldGroup>
  );
}
