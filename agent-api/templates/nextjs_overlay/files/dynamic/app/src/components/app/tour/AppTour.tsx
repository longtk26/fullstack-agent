"use client";

import { Compass } from "lucide-react";
import { usePathname, useRouter } from "next/navigation";
import { useCallback, useEffect, useMemo, useState } from "react";
import { EVENTS, Joyride, STATUS, type EventData, type Step } from "react-joyride";
import { Button } from "@/components/ui/button";
import { app, type TTour, type TTourStep } from "../app";
import { t } from "../messages";
import { useSession } from "../plugins";

/** Story 26.4: the guided tour of the app's core business workflows (`app.json` `workflows`, written by the agent
 *  from the draft's binding). It starts once per role and tour version on first sign-in, and the "Guide" button
 *  replays it (or the next workflow). It never blocks the app: a step whose target is not on the screen is shown in
 *  the middle of the page instead, and a step another role takes is a short note. */

const STORE = "bga-tour";

function seen(key: string): boolean {
  try {
    // `bga-tour-off`: a browser that must see the screens without the tour (the agent's evaluation)
    return window.localStorage.getItem(key) === "done" || window.localStorage.getItem("bga-tour-off") === "1";
  } catch {
    return true; // no storage (private mode): never start on its own
  }
}

function remember(key: string) {
  try {
    window.localStorage.setItem(key, "done");
  } catch {
    // the tour shows again next time
  }
}

function pattern(route: string): RegExp {
  const body = route
    .split("/")
    .map((part) => (part.startsWith("[") ? "[^/]+" : part.replace(/[.*+?^${}()|\\]/g, "\\$&")))
    .join("/");
  return new RegExp(`^${body}/?$`);
}

export function tourTarget(step: TTourStep): HTMLElement | null {
  if (!step.target || typeof document === "undefined") return null;
  const section = `[data-bga-section="${step.page}/${step.target.section}"]`;
  const action = step.target.action ? document.querySelector<HTMLElement>(`${section} [data-bga-action="${step.target.action}"]`) : null;
  return action ?? document.querySelector<HTMLElement>(section);
}

async function waitFor<T>(find: () => T | null, ms = 6000): Promise<T | null> {
  const started = Date.now();
  let found = find();
  while (!found && Date.now() - started < ms) {
    await new Promise((resolve) => setTimeout(resolve, 150));
    found = find();
  }
  return found;
}

/** A link on the page to one record under `prefix` (`/contractors/repair-requests` → `/contractors/repair-requests/<id>`):
 *  the id of the first one, as the kit's lists render their rows (`<a href>` to the record page). */
function recordLink(prefix: string): string | null {
  const base = prefix === "/" ? "" : prefix;
  for (const anchor of Array.from(document.querySelectorAll<HTMLAnchorElement>("a[href]"))) {
    const path = new URL(anchor.href, window.location.origin).pathname;
    if (!path.startsWith(`${base}/`)) continue;
    const rest = path.slice(base.length + 1);
    if (rest && !rest.includes("/") && rest !== "new") return rest;
  }
  return null;
}

/** Opens a page of the route, records included: each `[param]` is the record the user is on (same prefix), else the
 *  first record linked from the list page at that prefix. False when there is no record to open (the step then stays
 *  in the middle of the page and asks the user to open one). */
async function openRoute(route: string, push: (href: string) => void): Promise<boolean> {
  if (pattern(route).test(window.location.pathname)) return true;
  const parts = route.split("/");
  const resolved: string[] = [];
  for (let index = 0; index < parts.length; index++) {
    const part = parts[index];
    if (!part.startsWith("[")) {
      resolved.push(part);
      continue;
    }
    const prefix = resolved.join("/") || "/";
    const current = window.location.pathname.split("/");
    const here = current.slice(0, index).join("/") === resolved.join("/") ? current[index] : undefined;
    let value: string | null = here && here !== "new" ? here : null;
    if (!value) {
      if (window.location.pathname !== prefix) push(prefix);
      value = await waitFor(() => recordLink(prefix));
    }
    if (!value) return false;
    resolved.push(value);
  }
  push(resolved.join("/"));
  return true;
}

/** "Open a record to continue": only while the step's target is not on the screen (the tour could not open one). */
function RecordHint({ step }: { step: TTourStep }) {
  const [missing, setMissing] = useState(false);
  useEffect(() => setMissing(!tourTarget(step)), [step]);
  return missing ? <span className="mt-1 block text-xs opacity-70">{t("tourOpenRecord", { action: step.title })}</span> : null;
}

/** The joyride steps of one tour for one role (exported for the tests). */
export function tourSteps(tour: TTour, role: string | null, push: (href: string) => void): Step[] {
  const mine = (step: TTourStep) => !role || !step.role || step.role === role;
  const steps: Step[] = tour.steps.map((step) => {
    const center = { target: "body", placement: "center" as const, id: step.id };
    if (step.automatic) return { ...center, content: t("tourAutomatic", { action: step.title }) };
    if (!mine(step)) return { ...center, content: t("tourOtherRole", { actor: step.actor, action: step.title }) };
    if (step.skip || !step.target) return { ...center, content: step.title };
    const route = step.route;
    return {
      id: step.id,
      title: step.actor,
      content: (
        <span data-bga-tour-step={step.id}>
          {step.title}
          {route && route.includes("[") ? <RecordHint step={step} /> : null}
        </span>
      ),
      target: () => tourTarget(step) ?? document.body,
      placement: "auto",
      before: async () => {
        // go to the step's page (a record page: open one) and wait for the control the step points at
        if (route && !pattern(route).test(window.location.pathname) && !(await openRoute(route, push))) return;
        await waitFor(() => tourTarget(step));
      },
    };
  });
  if (tour.outcome) {
    steps.push({ target: "body", placement: "center", id: "outcome", content: t("tourDoneWhen", { outcome: tour.outcome }) });
  }
  return steps;
}

export default function AppTour() {
  const workflows = app.workflows;
  const session = useSession();
  const router = useRouter();
  const pathname = usePathname();
  const role = session.enabled ? ((session.user?.role as string | undefined) ?? null) : null;
  const signedIn = !session.enabled || Boolean(session.user);
  const tours = useMemo(
    () => (workflows?.tours ?? []).filter((tour) => !role || tour.roles.length === 0 || tour.roles.includes(role)),
    [workflows, role],
  );
  const [index, setIndex] = useState(0);
  const [run, setRun] = useState(false);
  const who = `${role ?? "everyone"}:${String(session.user?.id ?? "")}`;
  const key = `${STORE}:${workflows?.version ?? ""}:${who}`;

  useEffect(() => {
    // first sign-in of this user and role for this tour version: once, never on the sign-in pages themselves
    if (!session.ready || !signedIn || tours.length === 0 || run) return;
    if (pathname?.startsWith("/login") || pathname?.startsWith("/register")) return;
    if (seen(key)) return;
    const timer = setTimeout(() => setRun(true), 800);
    return () => clearTimeout(timer);
  }, [session.ready, signedIn, tours.length, key, pathname, run]);

  const push = useCallback((href: string) => router.push(href), [router]);
  const tour = tours[index % Math.max(tours.length, 1)];
  const steps = useMemo(() => (tour ? tourSteps(tour, role, push) : []), [tour, role, push]);

  const onEvent = useCallback(
    (data: EventData) => {
      if (data.type === EVENTS.TOUR_END || data.status === STATUS.FINISHED || data.status === STATUS.SKIPPED) {
        remember(key);
        setRun(false);
      }
    },
    [key],
  );

  if (!workflows || tours.length === 0 || !signedIn) return null;
  return (
    <>
      <Joyride
        run={run}
        steps={steps}
        continuous
        scrollToFirstStep
        onEvent={onEvent}
        options={{
          showProgress: true,
          buttons: ["back", "skip", "primary"],
          overlayClickAction: false,
          zIndex: 60,
          beforeTimeout: 15000, // a record step opens a list, then a record (`openRoute`)
          skipBeacon: true, // the step itself, not a pulsing dot to click first (a first sign-in saw no tour)
        }}
        locale={{ back: t("tourBack"), next: t("tourNext"), last: t("tourDone"), skip: t("tourSkip") }}
      />
      <Button
        type="button"
        variant="outline"
        size="sm"
        className="fixed right-4 bottom-20 z-40 shadow-md md:bottom-4"
        data-bga-guide
        title={tour ? t("guideTitle", { name: tour.name }) : t("guide")}
        onClick={() => {
          if (run) setIndex((value) => value + 1);
          setRun(false);
          setTimeout(() => setRun(true), 50);
        }}
      >
        <Compass data-icon="inline-start" aria-hidden />
        {t("guide")}
      </Button>
    </>
  );
}
