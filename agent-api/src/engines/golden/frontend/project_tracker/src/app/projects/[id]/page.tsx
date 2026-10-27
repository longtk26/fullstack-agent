import type { Metadata } from "next";
import { ProjectPage } from "@/features/projects/components/ProjectPage";

export const metadata: Metadata = { title: "Project" };

type PageProps = {
  params: Promise<{ id: string }>;
};

export default async function Page({ params }: PageProps) {
  const { id } = await params;
  return <ProjectPage id={id} />;
}
