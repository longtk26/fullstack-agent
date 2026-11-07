"use client";

import dynamic from "next/dynamic";
import { app } from "../app";

/** Story 26.4: the tour's code (react-joyride) loads only for an app whose draft found business workflows. */
const AppTour = dynamic(() => import("./AppTour"), { ssr: false });

export function TourMount() {
  return app.workflows?.tours?.length ? <AppTour /> : null;
}
