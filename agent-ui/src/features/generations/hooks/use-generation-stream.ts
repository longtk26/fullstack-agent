"use client";

import { useEffect, useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { generationEventsUrl } from "../api/generations-api";
import { isTerminal } from "../lib/status";
import { generationKeys } from "../query-keys";
import type { TGenerationDetail, TGenerationEvent, TGenerationStatus } from "../types";

export type TStreamState = "connecting" | "open" | "reconnecting" | "closed";

const FLUSH_MS = 100;
const DETAIL_REFRESH_MS = 400;
const RECONNECT_MS = 3000;
const MAX_EVENTS = 10_000;
const REFRESHING_TYPES = new Set(["status.changed", "step.started", "step.finished", "engine.finished", "job.resumed"]);

function isTerminalEvent(event: TGenerationEvent): boolean {
  return event.type === "status.changed" && isTerminal(event.status);
}

/**
 * Streams a generation's SSE events into the React Query cache: the event list under `events(id)`, and
 * status / current step patched into `detail(id)` (plus a debounced refetch for steps and usage).
 * The list survives remounts; reconnects resume after the last seen id, so nothing is duplicated.
 */
export function useGenerationStream(id: string) {
  const queryClient = useQueryClient();
  const eventsKey = generationKeys.events(id);
  const [state, setState] = useState<TStreamState>("connecting");

  const { data: events = [] } = useQuery<TGenerationEvent[]>({
    queryKey: eventsKey,
    queryFn: () => queryClient.getQueryData<TGenerationEvent[]>(eventsKey) ?? [],
    initialData: [],
    staleTime: Infinity,
  });

  useEffect(() => {
    const detailKey = generationKeys.detail(id);
    const cached = queryClient.getQueryData<TGenerationEvent[]>(generationKeys.events(id)) ?? [];
    let lastId = cached.at(-1)?.id ?? 0;
    let finished = cached.some(isTerminalEvent);
    let source: EventSource | null = null;
    let buffer: TGenerationEvent[] = [];
    let flushTimer: ReturnType<typeof setTimeout> | undefined;
    let refreshTimer: ReturnType<typeof setTimeout> | undefined;
    let reconnectTimer: ReturnType<typeof setTimeout> | undefined;

    const refreshDetail = () => {
      clearTimeout(refreshTimer);
      refreshTimer = setTimeout(() => {
        queryClient.invalidateQueries({ queryKey: detailKey });
        queryClient.invalidateQueries({ queryKey: generationKeys.lists() });
      }, DETAIL_REFRESH_MS);
    };

    const flush = () => {
      flushTimer = undefined;
      const batch = buffer;
      buffer = [];
      if (batch.length === 0) return;
      queryClient.setQueryData<TGenerationEvent[]>(generationKeys.events(id), (previous = []) =>
        [...previous, ...batch].slice(-MAX_EVENTS),
      );
      const lastStatus = batch.findLast((event) => event.type === "status.changed");
      if (lastStatus) {
        queryClient.setQueryData<TGenerationDetail>(detailKey, (detail) =>
          detail
            ? {
                ...detail,
                status: lastStatus.status as TGenerationStatus,
                currentStep: lastStatus.step ?? detail.currentStep,
              }
            : detail,
        );
      }
      if (batch.some((event) => REFRESHING_TYPES.has(event.type))) refreshDetail();
    };

    const connect = () => {
      const url = lastId > 0 ? `${generationEventsUrl(id)}?after=${lastId}` : generationEventsUrl(id);
      source = new EventSource(url);
      source.onopen = () => setState("open");
      source.onmessage = (message) => {
        const event = JSON.parse(message.data) as TGenerationEvent;
        if (event.id <= lastId) return;
        lastId = event.id;
        buffer.push(event);
        flushTimer ??= setTimeout(flush, FLUSH_MS);
        if (isTerminalEvent(event)) {
          finished = true;
          source?.close();
          clearTimeout(flushTimer);
          flush();
          setState("closed");
        }
      };
      source.onerror = () => {
        if (finished) return;
        if (isTerminal(queryClient.getQueryData<TGenerationDetail>(detailKey)?.status)) {
          finished = true;
          source?.close();
          setState("closed");
          return;
        }
        // EventSource retries by itself (sending Last-Event-ID) unless the response was not a stream.
        if (source?.readyState === EventSource.CLOSED) {
          reconnectTimer = setTimeout(connect, RECONNECT_MS);
        }
        setState("reconnecting");
      };
    };

    if (!finished) connect();
    return () => {
      source?.close();
      clearTimeout(flushTimer);
      clearTimeout(refreshTimer);
      clearTimeout(reconnectTimer);
      flush();
    };
  }, [id, queryClient]);

  return { events, state: events.some(isTerminalEvent) ? "closed" : state };
}
