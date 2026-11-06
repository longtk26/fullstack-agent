"use client";

import { ChevronsUpDownIcon, XIcon } from "lucide-react";
import { useDeferredValue, useState } from "react";
import { Button } from "@/components/ui/button";
import { Command, CommandEmpty, CommandGroup, CommandInput, CommandItem, CommandList } from "@/components/ui/command";
import { Popover, PopoverContent, PopoverTrigger } from "@/components/ui/popover";
import { Skeleton } from "@/components/ui/skeleton";
import { app, listOf, recordTitle, type TRecord } from "../app";
import { useOperationQuery } from "../bindings";
import type { TFieldProps } from "./types";
import { inSentence, t } from "../messages";


/** A record's name in the picker: the contract's label field, else the outline's display field. */
function nameOf(entity: string, labelField: string | undefined, record: TRecord): string {
  const value = labelField ? record[labelField] : undefined;
  return value === undefined || value === null || value === "" ? recordTitle(app.entities[entity], record) : String(value);
}

/** A reference (`x-bga.source: "reference"`, Story 22.6): the user picks the related record by its name, the form
 *  sends its id. Never an id input. A parent fixed by the route is a hidden field instead (the screen planner). */
export function ReferenceField({ field, id, value, onChange, invalid }: TFieldProps) {
  const reference = field.reference!;
  const [open, setOpen] = useState(false);
  const [query, setQuery] = useState("");
  const deferred = useDeferredValue(query);
  // the first page (the planner's size, within the list's limit), searched on the server when the list has search
  const params: Record<string, unknown> = reference.limitParam ? { [reference.limitParam]: reference.pageSize ?? 50 } : {};
  if (reference.searchParam && deferred) params[reference.searchParam] = deferred;
  const list = useOperationQuery(reference.listOperation, params);
  const { records } = listOf(list.data);
  const chosen = value === undefined || value === null || value === "" ? undefined : String(value);
  const listed = chosen ? records.find((record) => String(record.id) === chosen) : undefined;
  // the chosen record when the first page does not hold it (an edit form): its own `get`
  const own = useOperationQuery(chosen && !listed && !list.isLoading ? reference.detailOperation : undefined, { id: chosen });
  const current = listed ?? (own.data as TRecord | undefined);
  const entityLabel = app.entities[reference.entity]?.label ?? reference.entity;

  return (
    <div className="flex items-center gap-1">
      <Popover open={open} onOpenChange={setOpen}>
        <PopoverTrigger
          render={
            <Button
              id={id}
              type="button"
              variant="outline"
              role="combobox"
              aria-expanded={open}
              aria-invalid={invalid || undefined}
              data-bga-input="reference"
              className="w-full min-w-0 shrink justify-between font-normal data-[empty=true]:text-muted-foreground"
              data-empty={!chosen}
            />
          }
        >
          <span className="truncate">{current ? nameOf(reference.entity, reference.labelField, current) : chosen ? "…" : `Choose a ${entityLabel.toLowerCase()}`}</span>
          <ChevronsUpDownIcon aria-hidden className="size-4 opacity-60" />
        </PopoverTrigger>
        <PopoverContent className="w-(--anchor-width) min-w-64 p-0" align="start">
          <Command shouldFilter={!reference.searchParam}>
            <CommandInput placeholder={`${t("search", { name: inSentence(app.entities[reference.entity]?.plural ?? entityLabel) })}…`} value={query} onValueChange={setQuery} />
            <CommandList>
              {list.isLoading ? (
                <div className="flex flex-col gap-1 p-2" aria-busy="true">
                  <Skeleton className="h-7 w-full" />
                  <Skeleton className="h-7 w-full" />
                </div>
              ) : (
                <>
                  <CommandEmpty>{list.isError ? t("couldNotLoadList") : t("nothingFound")}</CommandEmpty>
                  <CommandGroup>
                    {records.map((record) => {
                      const name = nameOf(reference.entity, reference.labelField, record);
                      const key = String(record.id);
                      return (
                        <CommandItem
                          key={key}
                          value={key}
                          keywords={[name]}
                          data-checked={key === chosen}
                          onSelect={() => {
                            onChange(record.id);
                            setOpen(false);
                            setQuery("");
                          }}
                        >
                          <span className="truncate">{name}</span>
                        </CommandItem>
                      );
                    })}
                  </CommandGroup>
                </>
              )}
            </CommandList>
          </Command>
        </PopoverContent>
      </Popover>
      {!field.required && chosen && (
        <Button type="button" variant="ghost" size="icon" aria-label={t("clear", { name: field.label ?? field.name })} onClick={() => onChange(undefined)}>
          <XIcon aria-hidden />
        </Button>
      )}
    </div>
  );
}
