"use client";

import { Label } from "@/components/ui/label";
import { RadioGroup, RadioGroupItem } from "@/components/ui/radio-group";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { ToggleGroup, ToggleGroupItem } from "@/components/ui/toggle-group";
import { enumLabel, type TFieldProps } from "./types";

const TOGGLE_MAX = 3; // values side by side as a segmented control
const TOGGLE_LABEL_MAX = 12;
const RADIO_MAX = 5;

/** How an enum is picked: a segmented control for up to 3 short values, radios up to 5, else a Select. */
export function choiceStyle(values: string[]): "toggle" | "radio" | "select" {
  if (values.length <= TOGGLE_MAX && values.every((value) => enumLabel(value).length <= TOGGLE_LABEL_MAX)) return "toggle";
  return values.length <= RADIO_MAX ? "radio" : "select";
}

/** `enum` (Story 22.5): the contract's values, labelled. */
export function ChoiceField({ field, id, value, onChange, invalid }: TFieldProps) {
  const values = field.values ?? [];
  const current = typeof value === "string" ? value : undefined;
  const label = field.label ?? field.name;
  switch (choiceStyle(values)) {
    case "toggle":
      return (
        <ToggleGroup
          id={id}
          variant="outline"
          spacing={0}
          aria-label={label}
          aria-invalid={invalid || undefined}
          data-bga-input="toggle"
          className="w-full justify-start"
          value={current ? [current] : []}
          onValueChange={(next: unknown[]) => {
            // a required choice stays chosen (clicking the chosen value again does not clear it)
            const picked = next[0] as string | undefined;
            if (picked !== undefined || !field.required) onChange(picked);
          }}
        >
          {values.map((option) => (
            <ToggleGroupItem key={option} value={option} className="flex-1 sm:flex-none">
              {enumLabel(option)}
            </ToggleGroupItem>
          ))}
        </ToggleGroup>
      );
    case "radio":
      return (
        <RadioGroup
          id={id}
          aria-label={label}
          aria-invalid={invalid || undefined}
          data-bga-input="radio"
          value={current ?? null}
          onValueChange={(next: unknown) => onChange(next as string)}
          className="flex flex-wrap gap-x-5 gap-y-2"
        >
          {values.map((option) => (
            <div key={option} className="flex items-center gap-2">
              <RadioGroupItem id={`${id}-${option}`} value={option} aria-invalid={invalid || undefined} />
              <Label htmlFor={`${id}-${option}`} className="font-normal">
                {enumLabel(option)}
              </Label>
            </div>
          ))}
        </RadioGroup>
      );
    default:
      return (
        <Select
          items={Object.fromEntries(values.map((option) => [option, enumLabel(option)]))}
          value={current ?? null}
          onValueChange={(next) => onChange(next ?? undefined)}
        >
          <SelectTrigger id={id} className="w-full" aria-invalid={invalid || undefined} data-bga-input="select">
            <SelectValue placeholder="Choose…" />
          </SelectTrigger>
          <SelectContent>
            {values.map((option) => (
              <SelectItem key={option} value={option}>
                {enumLabel(option)}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      );
  }
}
