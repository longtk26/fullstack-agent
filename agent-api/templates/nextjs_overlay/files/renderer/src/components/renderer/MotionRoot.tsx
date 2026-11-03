"use client";

import { useEffect, useLayoutEffect } from "react";

// A section reveals once this much of it is in view (or this many pixels, for sections taller than the screen).
const VISIBLE_RATIO = 0.15;
const VISIBLE_PX = 240;

/**
 * Reveals the page's sections as they come into view, once each (Story 20.6). The page's inline script turned motion
 * on (`html[data-motion="on"]`) only when JavaScript runs and the visitor has not asked for reduced motion; this marks
 * that the page is alive (`data-motion-ready`, so the script's safety timer keeps motion on) and sets
 * `data-revealed` on each section, which the CSS in `globals.css` animates. A page rendered in the browser (a dynamic
 * app behind its mock gate) never ran the script, so motion is turned on here, before the first paint. Nothing renders.
 */
export function MotionRoot() {
  useLayoutEffect(() => {
    const root = document.documentElement;
    if (root.dataset.motion === undefined && !matchMedia("(prefers-reduced-motion: reduce)").matches) {
      root.dataset.motion = "on";
    }
  }, []);

  useEffect(() => {
    const root = document.documentElement;
    if (root.dataset.motion !== "on") return;
    root.dataset.motionReady = "1";
    const sections = document.querySelectorAll<HTMLElement>("[data-bga-section]:not([data-revealed])");
    if (!("IntersectionObserver" in window)) {
      sections.forEach((section) => section.setAttribute("data-revealed", ""));
      return;
    }
    const observer = new IntersectionObserver(
      (entries) => {
        for (const entry of entries) {
          const seen = entry.intersectionRatio >= VISIBLE_RATIO || entry.intersectionRect.height >= VISIBLE_PX;
          if (entry.isIntersecting && seen) {
            entry.target.setAttribute("data-revealed", "");
            observer.unobserve(entry.target);
          }
        }
      },
      { threshold: [0, 0.05, 0.1, VISIBLE_RATIO, 0.3] },
    );
    sections.forEach((section) => observer.observe(section));
    return () => observer.disconnect();
  }, []);
  return null;
}
