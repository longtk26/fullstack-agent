import { Section } from "@/components/layout/Section";
import { Separator } from "@/components/ui/separator";
import { formatValue, recordFields, recordKey, type TRecord } from "./records";
import type { TDataSectionContent } from "./types";

type ListProps = TDataSectionContent & {
  items?: TRecord[];
  fields?: string[];
};

/** Records of a content collection as a list: the first field as the line, the others below it. */
export function List({ title, description, items = [], fields }: ListProps) {
  const [primary, ...rest] = recordFields(items, fields);
  return (
    <Section title={title} description={description}>
      <ul className="flex flex-col">
        {items.map((record, index) => (
          <li key={recordKey(record, index)} className="flex flex-col gap-1">
            {index > 0 && <Separator className="mb-3" />}
            {primary && <span className="font-medium">{formatValue(record[primary])}</span>}
            {rest.map((field) => (
              <span key={field} className="text-sm text-muted-foreground">
                {formatValue(record[field])}
              </span>
            ))}
            <span className="pb-3" />
          </li>
        ))}
      </ul>
    </Section>
  );
}
