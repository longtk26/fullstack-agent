import type { Metadata } from "next";
import { OverviewPage } from "@/features/projects/components/OverviewPage";

export const metadata: Metadata = { title: "Overview" };

export default function HomePage() {
  return <OverviewPage />;
}
