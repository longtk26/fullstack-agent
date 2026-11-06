"use client";

import { ChoiceField } from "./ChoiceField";
import { DateField, DateTimeField } from "./DateField";
import { BooleanField, NumberField, TextAreaField, TextField } from "./InputFields";
import type { TFieldProps } from "./types";

/** The form kit's input for each field kind (Story 22.5). No field is a native date input. */
export function FieldInput(props: TFieldProps) {
  switch (props.field.type) {
    case "date":
      return <DateField {...props} />;
    case "datetime":
      return <DateTimeField {...props} />;
    case "enum":
      return <ChoiceField {...props} />;
    case "boolean":
      return <BooleanField {...props} />;
    case "integer":
    case "number":
    case "decimal":
      return <NumberField {...props} />;
    case "text":
      return <TextAreaField {...props} />;
    default:
      return <TextField {...props} />;
  }
}

/** Fields that take the form's full width (the others share a row from a medium width). */
export function isWide(type: string): boolean {
  return type === "text";
}
