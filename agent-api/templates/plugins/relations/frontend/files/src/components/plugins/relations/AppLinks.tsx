"use client";

import { Plus, X } from "lucide-react";
import Link from "next/link";
import { useParams } from "next/navigation";
import { useState } from "react";
import { toast } from "sonner";
import { app, canUse, listOf, pageHref, resolveParams, type TRouteParams } from "@/components/app/app";
import { useOperationMutation, useOperationQuery } from "@/components/app/bindings";
import { errorMessage } from "@/components/app/errors";
import { ReferenceField } from "@/components/app/form/ReferenceField";
import { useSession } from "@/components/app/plugins";
import type { TSectionSlot } from "@/components/app/plugin-types";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";

/** A record's many-to-many links (Story 22.7, relations): the linked records as chips (linked to their page), one
 *  added with a picker on the linked entity's list, one removed by its chip's button. */
export const AppLinks: TSectionSlot = ({ section }) => {
  const route = (useParams() ?? {}) as TRouteParams;
  const session = useSession();
  const content = section.content ?? {};
  const params = resolveParams(section.data?.params, route);
  const links = useOperationQuery(section.data?.operationId, params);
  const add = useOperationMutation(content.add?.operationId);
  const remove = useOperationMutation(content.remove?.operationId);
  const [chosen, setChosen] = useState<unknown>(undefined);
  const entity = content.entity ? app.entities[content.entity] : undefined;
  const { records } = listOf(links.data);
  const canAdd = Boolean(content.add) && canUse(content.add?.operationId, session);
  const canRemove = Boolean(content.remove) && canUse(content.remove?.operationId, session);
  const title = content.title ?? entity?.plural ?? "Links";

  function link() {
    if (!content.add || chosen === undefined) return;
    add.mutate(
      { params, body: { [content.add.field]: chosen } },
      {
        onSuccess: () => {
          setChosen(undefined);
          links.refetch();
        },
        onError: (error) => toast.error(errorMessage(content.add?.operationId, error)),
      },
    );
  }

  function unlink(id: unknown) {
    if (!content.remove) return;
    remove.mutate(
      { params: { ...params, [content.remove.param]: id }, body: {} },
      {
        onSuccess: () => links.refetch(),
        onError: (error) => toast.error(errorMessage(content.remove?.operationId, error)),
      },
    );
  }

  const href = entity?.detail;
  return (
    <div className="flex flex-col gap-4">
      <h2 className="sr-only">{title}</h2>
      {links.isLoading ? (
        <div className="flex gap-2" aria-busy="true">
          <Skeleton className="h-7 w-20" />
          <Skeleton className="h-7 w-24" />
        </div>
      ) : records.length === 0 ? (
        <p className="text-sm text-muted-foreground">No {title.toLowerCase()} yet.</p>
      ) : (
        <ul className="flex flex-wrap gap-2" aria-label={title}>
          {records.map((record) => {
            const label = String(record.label ?? record.id);
            return (
              <li key={String(record.id)}>
                <Badge variant="secondary" className="h-7 gap-1 pr-1 text-sm">
                  {href ? (
                    <Link href={pageHref(href, { id: record.id })} className="underline-offset-4 hover:underline">
                      {label}
                    </Link>
                  ) : (
                    label
                  )}
                  {canRemove && (
                    <Button
                      variant="ghost"
                      size="icon-xs"
                      className="size-5 rounded-full"
                      aria-label={`Remove ${label}`}
                      disabled={remove.isPending}
                      onClick={() => unlink(record.id)}
                      data-bga-action="unlink"
                    >
                      <X aria-hidden />
                    </Button>
                  )}
                </Badge>
              </li>
            );
          })}
        </ul>
      )}
      {canAdd && content.add && (
        <div className="flex max-w-md items-center gap-2" data-bga-links-add>
          <div className="min-w-0 flex-1">
            <ReferenceField
              id={`${section.id}-add`}
              field={{ name: content.add.field, type: "string", label: entity?.label, reference: content.add.reference }}
              value={chosen}
              onChange={setChosen}
              invalid={false}
            />
          </div>
          <Button size="sm" onClick={link} disabled={chosen === undefined || add.isPending} data-bga-action="link">
            <Plus data-icon="inline-start" aria-hidden />
            Add
          </Button>
        </div>
      )}
    </div>
  );
};
