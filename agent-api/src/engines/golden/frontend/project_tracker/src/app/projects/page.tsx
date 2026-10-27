import type { Metadata } from "next";
import { ProjectsPage } from "@/features/projects/components/ProjectsPage";

export const metadata: Metadata = { title: "Projects" };

export default function Page() {
  return <ProjectsPage />;
}
