import { Check, Minus } from "lucide-react";
import { Section } from "@/components/layout/Section";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { cn } from "@/lib/utils";
import { backdropImage } from "./AssetImage";
import type { TComparisonContent } from "./types";

type ComparisonProps = TComparisonContent;
type TValue = ComparisonProps["rows"][number]["values"][number];

function Value({ value }: { value: TValue }) {
  if (value === true) {
    return (
      <>
        <Check className="size-5 text-primary" aria-hidden />
        <span className="sr-only">Yes</span>
      </>
    );
  }
  if (value === false) {
    return (
      <>
        <Minus className="size-5 text-muted-foreground" aria-hidden />
        <span className="sr-only">No</span>
      </>
    );
  }
  return <>{value}</>;
}

/**
 * Options side by side (Story 20.8): `table` (a real table with row and column headers; it scrolls sideways on
 * small screens) or `cards` (one card per option listing every row). `true` / `false` show as a check and a dash.
 */
export function Comparison({ title, description, columns, rows, form = "table", background, backgroundImage }: ComparisonProps) {
  return (
    <Section title={title} description={description} background={background} backdrop={backdropImage(backgroundImage)}>
      {form === "cards" ? (
        <div className={cn("grid gap-6", columns.length === 2 ? "md:grid-cols-2" : "md:grid-cols-2 lg:grid-cols-3")}>
          {columns.map((column, index) => (
            <Card key={column}>
              <CardHeader>
                <CardTitle>{column}</CardTitle>
              </CardHeader>
              <CardContent>
                <dl className="flex flex-col divide-y divide-border">
                  {rows.map((row) => (
                    <div key={row.label} className="flex items-center justify-between gap-4 py-2">
                      <dt className="text-muted-foreground">{row.label}</dt>
                      <dd className="flex items-center text-right font-medium">
                        <Value value={row.values[index]} />
                      </dd>
                    </div>
                  ))}
                </dl>
              </CardContent>
            </Card>
          ))}
        </div>
      ) : (
        <div role="region" aria-label={title ?? "Comparison"} tabIndex={0} className="overflow-x-auto">
          <table className="w-full min-w-[32rem] text-left">
            <thead>
              <tr className="border-b border-border">
                <td className="py-3 pr-6" />
                {columns.map((column) => (
                  <th key={column} scope="col" className="px-4 py-3 text-lg font-semibold">
                    {column}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {rows.map((row) => (
                <tr key={row.label} className="border-b border-border last:border-0">
                  <th scope="row" className="py-3 pr-6 font-normal text-muted-foreground">
                    {row.label}
                  </th>
                  {row.values.map((value, index) => (
                    <td key={`${row.label}-${columns[index]}`} className="px-4 py-3">
                      <span className="flex items-center">
                        <Value value={value} />
                      </span>
                    </td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </Section>
  );
}
