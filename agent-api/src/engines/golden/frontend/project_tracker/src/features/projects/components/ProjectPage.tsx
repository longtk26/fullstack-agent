"use client";

import { DataTable } from "@/components/sections/DataTable";
import { DetailView } from "@/components/sections/DetailView";
import { Form } from "@/components/sections/Form";
import { QueryState } from "@/components/sections/QueryState";
import { useGetProject, useListTasks } from "@/lib/api/queries";
import { useNewTaskForm } from "@/features/tasks/hooks/use-new-task-form";

type ProjectPageProps = {
  id: string;
};

const STATUSES = ["TODO", "IN_PROGRESS", "DONE"] as const;

/** `/projects/[id]`: the project, its tasks by priority and the new-task form. */
export function ProjectPage({ id }: ProjectPageProps) {
  const project = useGetProject({ id });
  const tasks = useListTasks({ projectId: id, sort: "priority" });
  const newTask = useNewTaskForm(id);
  const rows = tasks.data?.items ?? [];
  return (
    <div className="flex flex-col gap-8">
      <QueryState isLoading={project.isLoading} error={project.error} isEmpty={!project.data} errorText="Could not load the project">
        {project.data && (
          <DetailView
            title={project.data.name}
            record={project.data}
            fields={[
              { key: "description", label: "Description" },
              { key: "createdAt", label: "Created", format: "datetime" },
            ]}
          />
        )}
      </QueryState>
      <section className="flex flex-col gap-4">
        <h2 className="text-lg font-semibold">Tasks</h2>
        <QueryState isLoading={tasks.isLoading} error={tasks.error} isEmpty={rows.length === 0} emptyText="No tasks yet">
          <DataTable
            rowKey="id"
            rows={rows}
            columns={[
              { key: "title", label: "Title" },
              { key: "status", label: "Status", format: "badge" },
              { key: "priority", label: "Priority" },
              { key: "dueDate", label: "Due", format: "date" },
            ]}
          />
        </QueryState>
      </section>
      <Form
        title="Add a task"
        form={newTask.form}
        onSubmit={newTask.onSubmit}
        pending={newTask.pending}
        submitLabel="Add task"
        fields={[
          { name: "title", label: "Title", type: "string" },
          { name: "status", label: "Status", type: "enum", values: STATUSES },
          { name: "priority", label: "Priority", type: "integer" },
          { name: "dueDate", label: "Due", type: "date" },
        ]}
      />
    </div>
  );
}
