"use client";

import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import { toast } from "sonner";
import { siteConfig } from "@/config/site";
import { Button } from "@/components/ui/button";
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
  AlertDialogTrigger,
} from "@/components/ui/alert-dialog";
import { useOperationMutation } from "@/components/renderer/bindings";
import type { TRecord, TSectionAction } from "@/components/renderer/site";

type ActionButtonsProps = {
  actions?: TSectionAction[];
  record?: TRecord;
  className?: string;
};

function resolveValue(val: unknown, record?: TRecord, route?: Record<string, unknown>): unknown {
  if (typeof val === "string") {
    if (val.startsWith("$record.") && record) {
      return record[val.slice("$record.".length)];
    }
    if (val.startsWith("$route.") && route) {
      const paramVal = route[val.slice("$route.".length)];
      return Array.isArray(paramVal) ? paramVal[0] : paramVal;
    }
  }
  return val;
}

export function ActionButton({ action, record }: { action: TSectionAction; record?: TRecord }) {
  const router = useRouter();
  const route = (useParams() ?? {}) as Record<string, unknown>;
  const mutation = useOperationMutation(action.operationId ?? undefined);

  if (action.kind === "link") {
    const rawTarget = action.page ?? "/";
    const pageRoute = (siteConfig.pages as Record<string, string>)[rawTarget] ?? rawTarget;
    let href = pageRoute;
    const params = action.params ?? {};
    for (const [key, rawVal] of Object.entries(params)) {
      const val = resolveValue(rawVal, record, route);
      href = href.replace(`[${key}]`, encodeURIComponent(String(val ?? "")));
    }
    if (record?.id !== undefined && !params.id && href.includes("[id]")) {
      href = href.replace("[id]", encodeURIComponent(String(record.id)));
    }
    const variant = action.variant ?? "outline";
    return (
      <Button asChild variant={variant} size="sm" data-bga-action={action.id}>
        <Link href={href}>{action.label}</Link>
      </Button>
    );
  }

  function execute() {
    const params: Record<string, unknown> = {};
    for (const [k, v] of Object.entries(action.params ?? {})) {
      params[k] = resolveValue(v, record, route);
    }
    if (record?.id !== undefined && params.id === undefined) {
      params.id = record.id;
    }
    const body: Record<string, unknown> = {};
    for (const [k, v] of Object.entries(action.body ?? {})) {
      body[k] = resolveValue(v, record, route);
    }

    mutation.mutate(
      { params, body },
      {
        onSuccess: () => {
          if (action.onSuccess?.toast) {
            toast.success(action.onSuccess.toast);
          }
          if (action.onSuccess?.navigate) {
            const target =
              (siteConfig.pages as Record<string, string>)[action.onSuccess.navigate] ?? action.onSuccess.navigate;
            router.push(target);
          }
        },
        onError: (err) => {
          toast.error(err.message);
        },
      },
    );
  }

  const isDelete = action.id.toLowerCase().includes("delete") || Boolean(action.operationId?.endsWith(".delete"));
  const defaultVariant = isDelete ? "destructive" : "outline";
  const variant = action.variant ?? defaultVariant;

  if (action.confirm) {
    const confirmMessage =
      typeof action.confirm === "string" ? action.confirm : "Are you sure you want to proceed?";
    return (
      <AlertDialog>
        <AlertDialogTrigger asChild>
          <Button variant={variant} size="sm" data-bga-action={action.id} disabled={mutation.isPending}>
            {action.label}
          </Button>
        </AlertDialogTrigger>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>{action.label}</AlertDialogTitle>
            <AlertDialogDescription>{confirmMessage}</AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Cancel</AlertDialogCancel>
            <AlertDialogAction variant={isDelete ? "destructive" : "default"} onClick={execute}>
              Confirm
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    );
  }

  return (
    <Button
      variant={variant}
      size="sm"
      data-bga-action={action.id}
      disabled={mutation.isPending}
      onClick={execute}
    >
      {action.label}
    </Button>
  );
}

export function ActionButtons({ actions = [], record, className }: ActionButtonsProps) {
  if (!actions.length) return null;
  return (
    <div className={className ?? "flex flex-wrap items-center gap-2"}>
      {actions.map((action) => (
        <ActionButton key={action.id} action={action} record={record} />
      ))}
    </div>
  );
}
