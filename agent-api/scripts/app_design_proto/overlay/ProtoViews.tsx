"use client";

// Story 23.0 prototype only: list views chosen by the design brief (media grid, feed, cards by field roles). They
// present the same records, actions and links as the kit's AppList rows; the binding is untouched.
import Link from "next/link";
import { useParams, usePathname } from "next/navigation";
import { useState, type ComponentType } from "react";
import { Badge } from "@/components/ui/badge";
import { Card } from "@/components/ui/card";
import { cn } from "@/lib/utils";
import {
  enumLabel,
  pageHref,
  recordTitle,
  resolveParams,
  type TAppAction,
  type TAppEntity,
  type TAppSection,
  type TRecord,
  type TRouteParams,
} from "./app";
import { FieldValue } from "./FieldValue";
import { RowActions } from "./RecordActions";
import { useLayout, useProto, type TRoles } from "./design";

type RowsProps = { section: TAppSection; entity?: TAppEntity; records: TRecord[] };

function viewHref(actions: TAppAction[], record: TRecord, route: TRouteParams): string | undefined {
  const view = actions.find((action) => action.id === "view" && action.page);
  return view?.page ? pageHref(view.page, resolveParams(view.params, route, record), route) : undefined;
}

function hue(value: unknown): number {
  let hash = 0;
  for (const char of String(value)) hash = (hash * 31 + char.charCodeAt(0)) % 360;
  return hash;
}

function imageUrl(entity: TAppEntity | undefined, record: TRecord, field: string | undefined): string | null {
  if (!field) return null;
  const urlField = entity?.fields?.[field]?.urlField;
  const value = (urlField ? record[urlField] : null) ?? record[field];
  return typeof value === "string" && /^(https?:|data:|\/)/.test(value) ? value : null;
}

/** The record's image, or a placeholder drawn from its title (no broken images). */
function Media({ entity, record, field, className, title }: { entity?: TAppEntity; record: TRecord; field?: string; className?: string; title: string }) {
  const url = imageUrl(entity, record, field);
  const [failed, setFailed] = useState(false);
  const h = hue(title);
  if (url && !failed) {
    // eslint-disable-next-line @next/next/no-img-element
    return <img src={url} alt="" className={cn("object-cover", className)} onError={() => setFailed(true)} />;
  }
  // a placeholder (the mock API has no image files): the title's colour and initial, never the title again
  return (
    <div
      aria-hidden
      className={cn("relative overflow-hidden", className)}
      style={{
        background: `radial-gradient(120% 90% at 0% 0%, oklch(0.78 0.13 ${h}), transparent 60%), radial-gradient(120% 90% at 100% 100%, oklch(0.55 0.16 ${(h + 70) % 360}), transparent 65%), oklch(0.66 0.12 ${(h + 35) % 360})`,
      }}
    >
      <span className="absolute -right-2 -bottom-6 font-heading text-[7rem] leading-none font-bold text-white/25 select-none">
        {title.trim().slice(0, 1).toUpperCase()}
      </span>
    </div>
  );
}

function Avatar({ entity, record, field, label }: { entity?: TAppEntity; record: TRecord; field?: string; label: string }) {
  const url = imageUrl(entity, record, field);
  if (url) {
    // eslint-disable-next-line @next/next/no-img-element
    return <img src={url} alt="" className="size-8 shrink-0 rounded-full object-cover" />;
  }
  return (
    <span
      aria-hidden
      className="flex size-8 shrink-0 items-center justify-center rounded-full text-xs font-semibold text-white"
      style={{ background: `oklch(0.6 0.13 ${hue(label)})` }}
    >
      {label.slice(0, 1).toUpperCase()}
    </span>
  );
}

function plain(entity: TAppEntity | undefined, record: TRecord, field: string | undefined): string {
  if (!field) return "";
  const reference = entity?.references?.[field];
  if (reference) {
    const summary = record[reference.summary] as { label?: unknown } | null | undefined;
    return summary?.label ? String(summary.label) : "";
  }
  const value = record[field];
  if (value === null || value === undefined) return "";
  return entity?.fields?.[field]?.type === "enum" ? enumLabel(String(value)) : String(value);
}

function Meta({ entity, record, roles }: { entity?: TAppEntity; record: TRecord; roles: TRoles }) {
  const fields = (roles.meta ?? []).filter((field) => record[field] !== null && record[field] !== undefined);
  if (fields.length === 0) return null;
  return (
    <div className="flex flex-wrap items-center gap-x-1.5 text-sm text-muted-foreground">
      {fields.map((field, index) => (
        <span key={field} className="flex items-center gap-1.5">
          {index > 0 && <span aria-hidden>·</span>}
          <FieldValue entity={entity} field={field} record={record} link={false} />
        </span>
      ))}
    </div>
  );
}

function Stat({ entity, record, field }: { entity?: TAppEntity; record: TRecord; field?: string }) {
  if (!field || record[field] === null || record[field] === undefined) return null;
  const label = entity?.fieldLabels?.[field] ?? field;
  return (
    <span className="text-sm font-medium tabular-nums">
      <FieldValue entity={entity} field={field} record={record} link={false} />{" "}
      <span className="font-normal text-muted-foreground">{label.toLowerCase()}</span>
    </span>
  );
}

function MediaGrid({ section, entity, records, roles }: RowsProps & { roles: TRoles }) {
  const route = (useParams() ?? {}) as TRouteParams;
  const actions = section.content?.actions ?? [];
  return (
    <ul className="grid gap-x-5 gap-y-8 sm:grid-cols-2 lg:grid-cols-3 2xl:grid-cols-4" data-proto-view="media-grid">
      {records.map((record) => {
        const title = roles.title ? plain(entity, record, roles.title) || recordTitle(entity, record) : recordTitle(entity, record);
        const href = viewHref(actions, record, route);
        const badge = plain(entity, record, roles.badge);
        const subtitle = plain(entity, record, roles.subtitle);
        return (
          <li key={String(record.id)} className="group flex flex-col gap-3">
            <Card className="relative overflow-hidden p-0" data-proto="media">
              <Media entity={entity} record={record} field={roles.media} title={title} className="aspect-video w-full transition-transform duration-300 group-hover:scale-[1.03]" />
              {badge && (
                <Badge className="absolute top-2 left-2" variant="secondary">
                  {badge}
                </Badge>
              )}
              {href && <Link href={href} className="absolute inset-0" aria-label={title} />}
            </Card>
            <div className="flex gap-3">
              {roles.avatar !== undefined && <Avatar entity={entity} record={record} field={roles.avatar} label={subtitle || title} />}
              <div className="flex min-w-0 flex-1 flex-col gap-0.5">
                <h3 className="line-clamp-2 font-semibold leading-snug">
                  {href ? (
                    <Link href={href} className="underline-offset-4 hover:underline">
                      {title}
                    </Link>
                  ) : (
                    title
                  )}
                </h3>
                {subtitle && <p className="truncate text-sm text-muted-foreground">{subtitle}</p>}
                <Meta entity={entity} record={record} roles={roles} />
                <Stat entity={entity} record={record} field={roles.stat ?? roles.price} />
              </div>
              <RowActions actions={actions} record={record} label={title} />
            </div>
          </li>
        );
      })}
    </ul>
  );
}

function Feed({ section, entity, records, roles }: RowsProps & { roles: TRoles }) {
  const route = (useParams() ?? {}) as TRouteParams;
  const actions = section.content?.actions ?? [];
  return (
    <ul className="mx-auto flex w-full max-w-2xl flex-col gap-5" data-proto-view="feed">
      {records.map((record) => {
        const title = roles.title ? plain(entity, record, roles.title) || recordTitle(entity, record) : recordTitle(entity, record);
        const href = viewHref(actions, record, route);
        // who it is from: a parent (the source, the channel) named in a role, else the subtitle
        const fromField = [roles.badge, roles.subtitle, roles.avatar].find((f) => f && entity?.references?.[f]);
        const from = plain(entity, record, fromField) || plain(entity, record, roles.subtitle);
        const summary = fromField === roles.subtitle || !roles.subtitle ? "" : plain(entity, record, roles.subtitle);
        const badge = roles.badge === fromField ? "" : plain(entity, record, roles.badge);
        return (
          <li key={String(record.id)}>
            <Card className="gap-3 p-5" data-proto="feed-item">
              <div className="flex items-center gap-3">
                <Avatar entity={entity} record={record} field={fromField ? undefined : roles.avatar} label={from || title} />
                <div className="min-w-0 flex-1">
                  {from && from !== summary && <p className="truncate text-sm font-semibold">{from}</p>}
                  <Meta entity={entity} record={record} roles={roles} />
                </div>
                <RowActions actions={actions} record={record} label={title} />
              </div>
              <h3 className="text-lg leading-snug font-semibold">
                {href ? (
                  <Link href={href} className="underline-offset-4 hover:underline">
                    {title}
                  </Link>
                ) : (
                  title
                )}
              </h3>
              {summary && <p className="line-clamp-2 text-sm text-muted-foreground">{summary}</p>}
              {roles.media && (
                <Media entity={entity} record={record} field={roles.media} title={title} className="aspect-[2.4/1] w-full rounded-lg" />
              )}
              <div className="flex items-center justify-between gap-2">
                <Stat entity={entity} record={record} field={roles.stat} />
                {badge && <Badge variant="outline">{badge}</Badge>}
              </div>
            </Card>
          </li>
        );
      })}
    </ul>
  );
}

function RoleCards({ section, entity, records, roles }: RowsProps & { roles: TRoles }) {
  const route = (useParams() ?? {}) as TRouteParams;
  const actions = section.content?.actions ?? [];
  return (
    <ul className="grid gap-4 sm:grid-cols-2 xl:grid-cols-3" data-proto-view="cards">
      {records.map((record) => {
        const title = roles.title ? plain(entity, record, roles.title) || recordTitle(entity, record) : recordTitle(entity, record);
        const href = viewHref(actions, record, route);
        const badge = plain(entity, record, roles.badge);
        const subtitle = plain(entity, record, roles.subtitle);
        return (
          <li key={String(record.id)}>
            <Card className="h-full gap-0 overflow-hidden p-0">
              {roles.media && <Media entity={entity} record={record} field={roles.media} title={title} className="aspect-[16/9] w-full" />}
              <div className="flex flex-1 flex-col gap-2 p-4">
                <div className="flex items-start justify-between gap-2">
                  <h3 className="line-clamp-2 font-semibold leading-snug">
                    {href ? (
                      <Link href={href} className="underline-offset-4 hover:underline">
                        {title}
                      </Link>
                    ) : (
                      title
                    )}
                  </h3>
                  <RowActions actions={actions} record={record} label={title} />
                </div>
                {subtitle && <p className="line-clamp-2 text-sm text-muted-foreground">{subtitle}</p>}
                <Meta entity={entity} record={record} roles={roles} />
                <div className="mt-auto flex items-center justify-between gap-2 pt-2">
                  {badge ? <Badge variant="secondary">{badge}</Badge> : <span />}
                  <Stat entity={entity} record={record} field={roles.price ?? roles.stat} />
                </div>
              </div>
            </Card>
          </li>
        );
      })}
    </ul>
  );
}

function CardBody({ entity, record, roles, href, actions, skip }: { entity?: TAppEntity; record: TRecord; roles: TRoles; href?: string; actions: TAppAction[]; skip?: string }) {
  const title = roles.title ? plain(entity, record, roles.title) || recordTitle(entity, record) : recordTitle(entity, record);
  const subtitle = plain(entity, record, roles.subtitle);
  const badge = roles.badge === skip ? "" : plain(entity, record, roles.badge);
  return (
    <>
      <div className="flex items-start justify-between gap-2">
        <p className="line-clamp-2 text-sm font-medium leading-snug">
          {href ? (
            <Link href={href} className="underline-offset-4 hover:underline">
              {title}
            </Link>
          ) : (
            title
          )}
        </p>
        <RowActions actions={actions} record={record} label={title} />
      </div>
      <Meta entity={entity} record={record} roles={roles} />
      <div className="flex items-center justify-between gap-2">
        <span className="flex min-w-0 items-center gap-2">
          {subtitle && (
            <>
              <Avatar entity={entity} record={record} label={subtitle} />
              <span className="truncate text-xs text-muted-foreground">{subtitle}</span>
            </>
          )}
        </span>
        {badge && <Badge variant="secondary">{badge}</Badge>}
      </div>
    </>
  );
}

/** Records in a column per status, in the flow's order (prototype: the loaded page; moving is the record's menu). */
function Board({ section, entity, records, roles, groupBy }: RowsProps & { roles: TRoles; groupBy: string }) {
  const route = (useParams() ?? {}) as TRouteParams;
  const actions = section.content?.actions ?? [];
  const states = entity?.fields?.[groupBy]?.values ?? [...new Set(records.map((r) => String(r[groupBy])))];
  return (
    <div className="-mx-1 flex gap-4 overflow-x-auto px-1 pb-2" data-proto-view="board">
      {states.map((state) => {
        const items = records.filter((record) => String(record[groupBy]) === state);
        return (
          <section key={state} className="flex w-72 shrink-0 flex-col gap-3 rounded-xl bg-muted/60 p-3" data-proto="column">
            <h3 className="flex items-center justify-between px-1 text-sm font-semibold">
              {enumLabel(state)}
              <span className="rounded-full bg-background px-2 text-xs tabular-nums text-muted-foreground">{items.length}</span>
            </h3>
            {items.map((record) => (
              <Card key={String(record.id)} className="gap-2 p-3">
                <CardBody entity={entity} record={record} roles={roles} actions={actions} href={viewHref(actions, record, route)} skip={groupBy} />
              </Card>
            ))}
            {items.length === 0 && <p className="px-1 py-6 text-center text-xs text-muted-foreground">Nothing here</p>}
          </section>
        );
      })}
    </div>
  );
}

function asDate(value: unknown): Date | null {
  if (typeof value !== "string") return null;
  const date = /^\d{4}-\d{2}-\d{2}$/.test(value) ? new Date(`${value}T00:00:00`) : new Date(value);
  return Number.isNaN(date.getTime()) ? null : date;
}
const dayKey = (date: Date) => `${date.getFullYear()}-${date.getMonth()}-${date.getDate()}`;

/** A month grid on wide screens, the agenda on phones (prototype: the loaded page's records). */
function Calendar({ section, entity, records, roles, dateField }: RowsProps & { roles: TRoles; dateField: string }) {
  const route = (useParams() ?? {}) as TRouteParams;
  const actions = section.content?.actions ?? [];
  const dated = records.map((record) => ({ record, date: asDate(record[dateField]) })).filter((x): x is { record: TRecord; date: Date } => x.date !== null);
  const counts = new Map<string, number>();
  for (const { date } of dated) counts.set(`${date.getFullYear()}-${date.getMonth()}`, (counts.get(`${date.getFullYear()}-${date.getMonth()}`) ?? 0) + 1);
  const [busiest] = [...counts.entries()].sort((a, b) => b[1] - a[1]);
  const [year, month] = busiest ? busiest[0].split("-").map(Number) : [new Date().getFullYear(), new Date().getMonth()];
  const first = new Date(year, month, 1);
  const start = new Date(year, month, 1 - ((first.getDay() + 6) % 7));
  const days = Array.from({ length: 42 }, (_, i) => new Date(start.getFullYear(), start.getMonth(), start.getDate() + i));
  const byDay = new Map<string, TRecord[]>();
  for (const { record, date } of dated) byDay.set(dayKey(date), [...(byDay.get(dayKey(date)) ?? []), record]);
  const time = new Intl.DateTimeFormat(undefined, { hour: "numeric", minute: "2-digit" });
  const timed = entity?.fields?.[dateField]?.type === "datetime";
  return (
    <>
      <div className="md:hidden">
        <Agenda section={section} entity={entity} records={records} roles={roles} dateField={dateField} />
      </div>
      <Card className="hidden gap-0 overflow-hidden p-0 md:flex" data-proto-view="calendar">
        <div className="flex items-center justify-between border-b px-4 py-3">
          <h3 className="font-semibold">{new Intl.DateTimeFormat(undefined, { month: "long", year: "numeric" }).format(first)}</h3>
          <span className="text-sm text-muted-foreground">{dated.length} on this page</span>
        </div>
        <div className="grid grid-cols-7 border-b text-xs font-medium text-muted-foreground">
          {["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"].map((d) => (
            <div key={d} className="px-2 py-1.5">{d}</div>
          ))}
        </div>
        <div className="grid grid-cols-7">
          {days.map((day) => {
            const items = byDay.get(dayKey(day)) ?? [];
            const outside = day.getMonth() !== month;
            return (
              <div key={day.toISOString()} className={cn("min-h-24 border-r border-b p-1.5 [&:nth-child(7n)]:border-r-0", outside && "bg-muted/40")}>
                <div className={cn("mb-1 text-xs tabular-nums", outside ? "text-muted-foreground/60" : "text-muted-foreground")}>{day.getDate()}</div>
                <div className="flex flex-col gap-1">
                  {items.slice(0, 3).map((record) => {
                    const title = roles.title ? plain(entity, record, roles.title) || recordTitle(entity, record) : recordTitle(entity, record);
                    const href = viewHref(actions, record, route);
                    const date = asDate(record[dateField]);
                    const chip = (
                      <span className="block truncate rounded-md bg-primary/12 px-1.5 py-0.5 text-xs text-foreground" style={{ borderLeft: `3px solid oklch(0.6 0.14 ${hue(plain(entity, record, roles.badge) || title)})` }}>
                        {timed && date && <span className="mr-1 tabular-nums text-muted-foreground">{time.format(date)}</span>}
                        {title}
                      </span>
                    );
                    return href ? <Link key={String(record.id)} href={href}>{chip}</Link> : <span key={String(record.id)}>{chip}</span>;
                  })}
                  {items.length > 3 && <span className="px-1 text-xs text-muted-foreground">+{items.length - 3} more</span>}
                </div>
              </div>
            );
          })}
        </div>
      </Card>
    </>
  );
}

/** The records by day, soonest first. */
function Agenda({ section, entity, records, roles, dateField }: RowsProps & { roles: TRoles; dateField: string }) {
  const route = (useParams() ?? {}) as TRouteParams;
  const actions = section.content?.actions ?? [];
  const dated = records
    .map((record) => ({ record, date: asDate(record[dateField]) }))
    .filter((x): x is { record: TRecord; date: Date } => x.date !== null)
    .sort((a, b) => a.date.getTime() - b.date.getTime());
  const groups: { day: Date; items: TRecord[] }[] = [];
  for (const { record, date } of dated) {
    const last = groups[groups.length - 1];
    if (last && dayKey(last.day) === dayKey(date)) last.items.push(record);
    else groups.push({ day: date, items: [record] });
  }
  const dayFormat = new Intl.DateTimeFormat(undefined, { weekday: "long", day: "numeric", month: "long" });
  const time = new Intl.DateTimeFormat(undefined, { hour: "numeric", minute: "2-digit" });
  const timed = entity?.fields?.[dateField]?.type === "datetime";
  return (
    <div className="flex flex-col gap-6" data-proto-view="agenda">
      {groups.map(({ day, items }) => (
        <section key={dayKey(day)} className="flex flex-col gap-2">
          <h3 className="text-sm font-semibold text-muted-foreground">{dayFormat.format(day)}</h3>
          {items.map((record) => {
            const date = asDate(record[dateField]);
            return (
              <Card key={String(record.id)} className="flex-row items-start gap-4 p-4">
                {timed && date && <span className="w-16 shrink-0 pt-0.5 text-sm font-semibold tabular-nums">{time.format(date)}</span>}
                <div className="flex min-w-0 flex-1 flex-col gap-1.5">
                  <CardBody entity={entity} record={record} roles={roles} actions={actions} href={viewHref(actions, record, route)} />
                </div>
              </Card>
            );
          })}
        </section>
      ))}
    </div>
  );
}

/** The brief's view of a list, or the kit's rows (`?proto=off`, a table, or no brief for the entity). */
export function ProtoRows({ Kit, ...props }: RowsProps & { Kit: ComponentType<RowsProps> }) {
  const proto = useProto();
  const pathname = usePathname();
  const layout = useLayout();
  const design = layout.entities[props.section.content?.entity ?? ""];
  if (!proto.on || !design || props.section.content?.variant === "recent") return <Kit {...props} />;
  // the kit reads one list style per entity for the whole app; an area's table must say so per section
  if (design.view === "table") return <Kit {...props} section={{ ...props.section, content: { ...props.section.content, style: "table" } }} />;
  if (design.view === "board" && design.groupBy) return <Board {...props} roles={design.roles} groupBy={design.groupBy} />;
  if (design.view === "calendar" && design.dateField) {
    if (pathname === "/" && layout.homeView === "agenda") return <Agenda {...props} roles={design.roles} dateField={design.dateField} />;
    return <Calendar {...props} roles={design.roles} dateField={design.dateField} />;
  }
  if (design.view === "media-grid") return <MediaGrid {...props} roles={design.roles} />;
  if (design.view === "feed") return <Feed {...props} roles={design.roles} />;
  return <RoleCards {...props} roles={design.roles} />;
}
