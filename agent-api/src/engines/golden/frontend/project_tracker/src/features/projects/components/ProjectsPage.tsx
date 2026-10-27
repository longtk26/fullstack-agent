"use client";

import { DataTable } from "@/components/sections/DataTable";
import { Form } from "@/components/sections/Form";
import { QueryState } from "@/components/sections/QueryState";
import { useListProjects } from "@/lib/api/queries";
import { useNewProjectForm } from "../hooks/use-new-project-form";

/** `/projects`: every project by name, and the new-project form. */
export function ProjectsPage() {
  const projects = useListProjects({ sort: "name" });
  const newProject = useNewProjectForm();
  const rows = projects.data?.items ?? [];
  return (
    <div className="flex flex-col gap-8">
      <h1 className="text-2xl font-semibold tracking-tight">Projects</h1>
      <QueryState isLoading={projects.isLoading} error={projects.error} isEmpty={rows.length === 0} emptyText="No projects yet">
        <DataTable
          rowKey="id"
          rows={rows}
          rowHref={(row) => `/projects/${String(row.id)}`}
          columns={[
            { key: "name", label: "Name" },
            { key: "createdAt", label: "Created", format: "datetime" },
          ]}
        />
      </QueryState>
      <Form
        title="New project"
        form={newProject.form}
        onSubmit={newProject.onSubmit}
        pending={newProject.pending}
        submitLabel="Create project"
        fields={[
          { name: "name", label: "Name", type: "string" },
          { name: "description", label: "Description", type: "text" },
        ]}
      />
    </div>
  );
}
