import type { TFormField } from "../app";

export { enumLabel } from "../app";

/** What every field component of the form kit takes (Story 22.5). */
export type TFieldProps = {
  field: TFormField;
  id: string;
  value: unknown;
  onChange: (value: unknown) => void;
  onBlur?: () => void;
  invalid: boolean;
};
