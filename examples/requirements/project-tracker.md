# Project Tracker — projects and their tasks for a small team

**Mode:** dynamic (web app with its own backend)
**Matches:** `frontend-specs/project-tracker-dynamic.json` + `specs/two-entity.json` (the fake engine can run it)

A small team wants one place to keep its projects and the tasks inside them. No logins for now.

## Pages

1. **Overview** — the six newest projects as cards (name and description); clicking one opens it.
2. **Projects** — every project in a table sorted by name (name, created), and a form to create a project with a
   name (required, up to 120 characters) and an optional description.
3. **Project** — one project's details, its tasks sorted by priority (title, status, priority, due date) and a
   form to add a task: title (required), status (To do, In progress, Done), priority (1–5) and due date.
4. **Tasks** — all open ("To do") tasks across projects, earliest due date first.

Navigation in a sidebar: Projects, Tasks. Dashboard look, compact spacing, light and dark mode.

## Data

- **Projects** — name (unique, required), description, created at.
- **Tasks** — belong to a project (deleting a project deletes its tasks); title (required, up to 200
  characters), status (To do by default), priority (1–5, 3 by default), due date.

Lists are paginated; tasks can be filtered by project and status and sorted by priority or due date.

## Done when

Projects and tasks can be created and listed in the browser; the same pages first work on example data and then
on the generated backend.
