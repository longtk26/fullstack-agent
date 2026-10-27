import type { Metadata } from "next";
import { TasksPage } from "@/features/tasks/components/TasksPage";

export const metadata: Metadata = { title: "Tasks" };

export default function Page() {
  return <TasksPage />;
}
