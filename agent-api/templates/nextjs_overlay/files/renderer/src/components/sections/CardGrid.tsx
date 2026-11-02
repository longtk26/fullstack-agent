"use client";

import Link from "next/link";
import { Grid } from "@/components/layout/Grid";
import { Section } from "@/components/layout/Section";
import { Card, CardContent, CardFooter, CardHeader, CardTitle } from "@/components/ui/card";
import { cn } from "@/lib/utils";
import type { TBinding, TColumn, TRecord, TSectionAction, TSectionControls, TStates } from "@/components/renderer/site";
import { recordHref } from "@/components/renderer/use-section-records";
import { ActionButtons } from "./ActionButtons";
import { AssetImage } from "./AssetImage";
import { formatValue } from "./format";
import { QueryState } from "./QueryState";
import { ControlledRecords } from "./SectionControls";
import { cardClass } from "./styles";
import type { TCardGridContent } from "./types";

type CardGridProps = TCardGridContent & {
  items?: TRecord[];
  columns?: TColumn[];
  binding?: TBinding;
  states?: TStates;
  actions?: TSectionAction[];
  controls?: TSectionControls;
};

/** Records as cards: image fields first, the first other field as the title; linked to the record's page. */
export function CardGrid({ title, description, cardStyle, items, columns = [], binding, states, actions = [], controls }: CardGridProps) {
  const images = columns.filter((column) => column.format === "image");
  const [heading, ...rest] = columns.filter((column) => column.format !== "image");
  const hasActions = actions.length > 0;

  return (
    <Section title={title} description={description}>
      <ControlledRecords items={items} binding={binding} controls={controls} columns={columns}>
        {({ records, isLoading, error }, controlsBar) => (
          <>
            {controlsBar}
            <QueryState isLoading={isLoading} error={error} isEmpty={records.length === 0} emptyText={states?.empty} emptyImage={states?.emptyImage} errorText={states?.error}>
              <Grid columns={3}>
                {records.map((record, index) => {
                  const href = recordHref(binding?.link, record);
                  const recordId = String(record.id ?? index);
                  const body = (
                    <>
                      {images.map((column) => (
                        <AssetImage key={column.key} asset={String(record[column.key] ?? "")} />
                      ))}
                      <CardHeader>{heading && <CardTitle>{formatValue(record[heading.key], heading.format)}</CardTitle>}</CardHeader>
                      {rest.length > 0 && (
                        <CardContent className="flex flex-col gap-1 text-sm text-muted-foreground">
                          {rest.map((column) => (
                            <span key={column.key}>{formatValue(record[column.key], column.format)}</span>
                          ))}
                        </CardContent>
                      )}
                    </>
                  );
                  return (
                    <div key={recordId} data-bga-record={recordId}>
                      <Card
                        className={cn(
                          cardClass(cardStyle),
                          "flex h-full flex-col justify-between",
                          href && "transition-transform duration-200 hover:-translate-y-0.5 motion-reduce:transition-none motion-reduce:hover:translate-y-0",
                        )}
                      >
                        {/* The link wraps the card's content only: the actions stay outside it (no <a> or button in <a>). */}
                        {href ? (
                          <Link href={href} className="block flex-1">
                            {body}
                          </Link>
                        ) : (
                          <div>{body}</div>
                        )}
                        {hasActions && (
                          <CardFooter className="pt-2">
                            <ActionButtons actions={actions} record={record} />
                          </CardFooter>
                        )}
                      </Card>
                    </div>
                  );
                })}
              </Grid>
            </QueryState>
          </>
        )}
      </ControlledRecords>
    </Section>
  );
}
