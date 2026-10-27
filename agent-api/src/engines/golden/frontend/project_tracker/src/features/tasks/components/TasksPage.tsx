"use client";

import { DataTable } from "@/components/sections/DataTable";
import { QueryState } from "@/components/sections/QueryState";
import { useListTasks } from "@/lib/api/queries";

/** `/tasks`: open tasks by due date. */
export function TasksPage() {
  const tasks = useListTasks({ status: "TODO", sort: "dueDate" });
  const rows = tasks.data?.items ?? [];
  return (
    <div className="flex flex-col gap-6">
      <h1 className="text-2xl font-semibold tracking-tight">Tasks</h1>
      <QueryState isLoading={tasks.isLoading} error={tasks.error} isEmpty={rows.length === 0} emptyText="Nothing to do">
        <DataTable
          rowKey="id"
          rows={rows}
          rowHref={(row) => `/projects/${String(row.projectId)}`}
          columns={[
            { key: "title", label: "Title" },
            { key: "status", label: "Status", format: "badge" },
            { key: "dueDate", label: "Due", format: "date" },
          ]}
        />
      </QueryState>
    </div>
  );
}
