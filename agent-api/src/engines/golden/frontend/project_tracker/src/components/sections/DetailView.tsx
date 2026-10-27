import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Separator } from "@/components/ui/separator";
import { formatValue, type TValueFormat } from "./format";

export type TDetailField = { key: string; label: string; format?: TValueFormat };

type DetailViewProps = {
  title: string;
  record: Record<string, unknown>;
  fields: TDetailField[];
};

/** One record: its title and labelled fields. */
export function DetailView({ title, record, fields }: DetailViewProps) {
  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-2xl">{title}</CardTitle>
      </CardHeader>
      <Separator />
      <CardContent>
        <dl className="grid gap-3 sm:grid-cols-[10rem_1fr]">
          {fields.map((field) => (
            <div key={field.key} className="contents">
              <dt className="text-sm text-muted-foreground">{field.label}</dt>
              <dd>{formatValue(record[field.key], field.format)}</dd>
            </div>
          ))}
        </dl>
      </CardContent>
    </Card>
  );
}
