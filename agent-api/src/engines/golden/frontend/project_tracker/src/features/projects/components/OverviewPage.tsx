"use client";

import { CardGrid } from "@/components/sections/CardGrid";
import { QueryState } from "@/components/sections/QueryState";
import { useListProjects } from "@/lib/api/queries";

/** `/`: the six newest projects. */
export function OverviewPage() {
  const projects = useListProjects({ limit: 6, sort: "-createdAt" });
  const items = (projects.data?.items ?? []).map((project) => ({
    key: project.id,
    title: project.name,
    description: project.description,
    href: `/projects/${project.id}`,
  }));
  return (
    <div className="flex flex-col gap-6">
      <h1 className="text-2xl font-semibold tracking-tight">Overview</h1>
      <QueryState isLoading={projects.isLoading} error={projects.error} isEmpty={items.length === 0} emptyText="No projects yet">
        <CardGrid items={items} />
      </QueryState>
    </div>
  );
}
