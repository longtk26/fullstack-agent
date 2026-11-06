"use client";

import { format, formatISO, isValid, parse, parseISO } from "date-fns";
import { CalendarIcon, XIcon } from "lucide-react";
import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Calendar } from "@/components/ui/calendar";
import { Input } from "@/components/ui/input";
import { Popover, PopoverContent, PopoverTrigger } from "@/components/ui/popover";
import { dateLocale } from "../date-locale";
import type { TFieldProps } from "./types";

const YEARS_BACK = 100;
const YEARS_AHEAD = 10;

function bounds() {
  const now = new Date();
  return {
    startMonth: new Date(now.getFullYear() - YEARS_BACK, 0),
    endMonth: new Date(now.getFullYear() + YEARS_AHEAD, 11),
  };
}

/** A `date` value (`YYYY-MM-DD`) as a local day, or undefined. */
function toDay(value: unknown): Date | undefined {
  if (typeof value !== "string" || !value) return undefined;
  const day = parse(value.slice(0, 10), "yyyy-MM-dd", new Date());
  return isValid(day) ? day : undefined;
}

/** A `datetime` value (ISO 8601) as a Date, or undefined. */
function toMoment(value: unknown): Date | undefined {
  if (typeof value !== "string" || !value) return undefined;
  const moment = parseISO(value);
  return isValid(moment) ? moment : undefined;
}

function Trigger({ id, invalid, text, placeholder }: { id: string; invalid: boolean; text?: string; placeholder: string }) {
  return (
    <PopoverTrigger
      render={
        <Button
          id={id}
          type="button"
          variant="outline"
          aria-invalid={invalid || undefined}
          data-bga-input="date"
          className="w-full min-w-0 shrink justify-start gap-2 font-normal data-[empty=true]:text-muted-foreground"
          data-empty={!text}
        />
      }
    >
      <CalendarIcon aria-hidden className="size-4 opacity-70" />
      <span className="truncate">{text ?? placeholder}</span>
    </PopoverTrigger>
  );
}

/** `date`: a calendar in a popover, shown in the app's locale, sent as `YYYY-MM-DD` (Story 22.5). */
export function DateField({ field, id, value, onChange, invalid }: TFieldProps) {
  const [open, setOpen] = useState(false);
  const day = toDay(value);
  return (
    <div className="flex items-center gap-1">
      <Popover open={open} onOpenChange={setOpen}>
        <Trigger id={id} invalid={invalid} text={day ? format(day, "PPP", { locale: dateLocale }) : undefined} placeholder="Pick a date" />
        <PopoverContent className="w-auto p-0" align="start">
          <Calendar
            mode="single"
            locale={dateLocale}
            selected={day}
            defaultMonth={day}
            captionLayout="dropdown"
            {...bounds()}
            onSelect={(next: Date | undefined) => {
              onChange(next ? format(next, "yyyy-MM-dd") : undefined);
              setOpen(false);
            }}
          />
        </PopoverContent>
      </Popover>
      {!field.required && day && (
        <Button type="button" variant="ghost" size="icon" aria-label={`Clear ${field.label ?? field.name}`} onClick={() => onChange(undefined)}>
          <XIcon aria-hidden />
        </Button>
      )}
    </div>
  );
}

/** `datetime`: a calendar and a time, sent as ISO 8601 with the browser's offset (Story 22.5). */
export function DateTimeField({ field, id, value, onChange, invalid }: TFieldProps) {
  const [open, setOpen] = useState(false);
  const moment = toMoment(value);
  const time = moment ? format(moment, "HH:mm") : "";

  function emit(day: Date | undefined, hhmm: string) {
    if (!day) return onChange(undefined);
    const [hours, minutes] = (hhmm || "09:00").split(":").map(Number);
    const next = new Date(day.getFullYear(), day.getMonth(), day.getDate(), hours || 0, minutes || 0);
    onChange(formatISO(next));
  }

  return (
    <div className="flex items-center gap-2">
      <div className="min-w-0 flex-1">
        <Popover open={open} onOpenChange={setOpen}>
          <Trigger id={id} invalid={invalid} text={moment ? format(moment, "PPP", { locale: dateLocale }) : undefined} placeholder="Pick a date" />
          <PopoverContent className="w-auto p-0" align="start">
            <Calendar
              mode="single"
              locale={dateLocale}
              selected={moment}
              defaultMonth={moment}
              captionLayout="dropdown"
              {...bounds()}
              onSelect={(next: Date | undefined) => {
                emit(next, time);
                setOpen(false);
              }}
            />
          </PopoverContent>
        </Popover>
      </div>
      <Input
        id={`${id}-time`}
        type="time"
        aria-label={`${field.label ?? field.name}, time`}
        className="w-36 shrink-0"
        value={time}
        disabled={!moment}
        onChange={(e) => emit(moment, e.target.value)}
      />
      {!field.required && moment && (
        <Button type="button" variant="ghost" size="icon" aria-label={`Clear ${field.label ?? field.name}`} onClick={() => onChange(undefined)}>
          <XIcon aria-hidden />
        </Button>
      )}
    </div>
  );
}
