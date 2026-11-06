"use client";

import { useQuery } from "@tanstack/react-query";
import { CircleCheck, CircleX, Clock } from "lucide-react";
import Link from "next/link";
import { useMemo, useState, useSyncExternalStore } from "react";
import type { TSectionSlot } from "@/components/app/plugin-types";
import { buttonVariants } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Spinner } from "@/components/ui/spinner";
import { fetchOperation } from "@/components/app/bindings";
import { PAYMENT_KEY } from "./PayAction";
import { t } from "@/components/app/messages";

type TPayment = { paymentId: string; status: "pending" | "paid" | "failed" | "canceled"; amount?: number; currency?: string };

/** The payment this return is about: from the address (the mock checkout adds it) or the session (the provider adds
 *  nothing), as one string so the snapshot is stable. */
function readStored(): string {
  let found: Record<string, unknown> = {};
  try {
    found = JSON.parse(sessionStorage.getItem(PAYMENT_KEY) ?? "{}") as Record<string, unknown>;
  } catch {
    // nothing stored
  }
  const fromQuery = new URLSearchParams(window.location.search).get("payment");
  return JSON.stringify(fromQuery ? { ...found, paymentId: fromQuery } : found);
}

const subscribe = () => () => {};

const POLL_MS = 1500;
const POLL_TRIES = 40; // about a minute: the provider's event settles the payment through a job

/** The checkout's return (Story 22.7): the payment from the address or the session, followed until it is paid,
 *  failed or canceled; then back to the record. */
export const AppPayment: TSectionSlot = ({ section }) => {
  const raw = useSyncExternalStore(subscribe, readStored, () => null);
  const stored = useMemo(() => (raw ? (JSON.parse(raw) as { paymentId?: string; back?: string }) : null), [raw]);
  const paymentId = stored?.paymentId;
  const status = section.data?.operationId ?? "payments.get";
  const [tries, setTries] = useState(0);
  const query = useQuery({
    queryKey: ["payment", paymentId],
    queryFn: async () => {
      setTries((count) => count + 1);
      return (await fetchOperation(status, { paymentId })) as TPayment;
    },
    enabled: Boolean(paymentId),
    refetchInterval: (current) => (current.state.data?.status === "pending" && tries < POLL_TRIES ? POLL_MS : false),
  });
  const payment = query.data;
  const settled = payment && payment.status !== "pending";
  const back = stored?.back ?? "/";
  const canceled = section.content?.variant === "cancel";
  let icon = <Spinner className="size-8" />;
  let title = t("confirmingPayment");
  let text = t("takesSeconds");
  if (stored && !paymentId) {
    icon = <CircleX aria-hidden className="size-8 text-muted-foreground" />;
    title = t("noPayment");
    text = t("startPayment");
  } else if (payment?.status === "paid") {
    icon = <CircleCheck aria-hidden className="size-8 text-primary" />;
    title = t("paymentReceived");
    text = payment.amount !== undefined ? t("paidThanks", { amount: `${payment.amount} ${payment.currency ?? ""}`.trim() }) : t("thanks");
  } else if (payment && settled) {
    icon = <CircleX aria-hidden className="size-8 text-destructive" />;
    title = payment.status === "failed" ? t("paymentFailed") : t("paymentCanceled");
    text = t("nothingCharged");
  } else if (canceled && !payment) {
    icon = <Clock aria-hidden className="size-8 text-muted-foreground" />;
  } else if (query.isError || (payment?.status === "pending" && tries >= POLL_TRIES)) {
    icon = <Clock aria-hidden className="size-8 text-muted-foreground" />;
    title = t("stillWaiting");
    text = t("checkAgain");
  }
  return (
    <div className="mx-auto w-full max-w-md pt-6" data-bga-payment={payment?.status ?? "pending"}>
      <Card>
        <CardHeader className="items-center text-center">
          <div className="mb-2 flex justify-center">{icon}</div>
          <CardTitle>
            <h1 className="text-xl font-semibold tracking-tight">{title}</h1>
          </CardTitle>
          <CardDescription>{text}</CardDescription>
        </CardHeader>
        <CardContent className="flex justify-center">
          <Link href={back} className={buttonVariants({ variant: settled ? "default" : "outline" })}>
            Back to the record
          </Link>
        </CardContent>
      </Card>
    </div>
  );
};
