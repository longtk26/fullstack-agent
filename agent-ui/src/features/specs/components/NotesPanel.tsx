import { CircleHelp, Lightbulb } from "lucide-react";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import type { TImportNote } from "../types";

type NotesPanelProps = {
  kind: "assumptions" | "unresolved";
  notes: TImportNote[];
};

export function NotesPanel({ kind, notes }: NotesPanelProps) {
  if (notes.length === 0) return null;
  const Icon = kind === "assumptions" ? Lightbulb : CircleHelp;
  return (
    <Alert variant={kind === "unresolved" ? "destructive" : "default"}>
      <Icon />
      <AlertTitle>
        {kind === "assumptions" ? "Assumptions" : "Unresolved"} ({notes.length})
      </AlertTitle>
      <AlertDescription>
        <ul className="flex list-disc flex-col gap-1 pl-4">
          {notes.map((note, index) => (
            <li key={`${note.path}-${index}`}>
              {note.message}
              <span className="ml-1 font-mono text-xs text-muted-foreground">{note.path}</span>
              {note.suggestion && <span className="block text-xs">Suggestion: {note.suggestion}</span>}
            </li>
          ))}
        </ul>
      </AlertDescription>
    </Alert>
  );
}
