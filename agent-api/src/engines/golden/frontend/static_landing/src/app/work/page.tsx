import type { Metadata } from "next";
import { Gallery } from "@/components/sections/Gallery";
import projects from "@/content/projects.json";

export const metadata: Metadata = { title: "Work" };

export default function WorkPage() {
  return <Gallery items={projects} />;
}
