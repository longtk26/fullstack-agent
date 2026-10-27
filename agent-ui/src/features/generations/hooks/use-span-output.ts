"use client";

import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { fetchSpanOutput } from "../api/generations-api";
import { generationKeys } from "../query-keys";
import type { TSpanStream, TTraceSpan } from "../types";

const FIRST_TAIL = 500;
const MAX_TAIL = 20_000;

/** Output excerpt of a span (CLI stdout/stderr, a check's output or a repair patch), tail-first with "load more". */
export function useSpanOutput(generationId: string, span: TTraceSpan | null) {
  const [stream, setStream] = useState<TSpanStream>("stdout");
  const [tail, setTail] = useState(FIRST_TAIL);
  const hasOutput = Boolean(span && (span.refs.stdout || span.refs.output || span.refs.patch));
  const output = useQuery({
    queryKey: generationKeys.spanOutput(generationId, span?.spanId ?? "", stream, tail),
    queryFn: () => fetchSpanOutput(generationId, span!.spanId, stream, tail),
    enabled: hasOutput,
    retry: false,
  });
  const lines = output.data ? output.data.text.split("\n").length : 0;

  return {
    hasOutput,
    hasStreams: Boolean(span?.refs.stderr),
    stream,
    setStream: (next: TSpanStream) => {
      setStream(next);
      setTail(FIRST_TAIL);
    },
    output,
    canLoadMore: lines >= tail && tail < MAX_TAIL,
    loadMore: () => setTail((current) => Math.min(MAX_TAIL, current * 4)),
    copy: () => output.data && navigator.clipboard.writeText(output.data.text),
  };
}
