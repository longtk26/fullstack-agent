import { Download } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { buttonVariants } from "@/components/ui/button";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { artifactUrl } from "../../api/generations-api";
import type { TArtifact } from "../../types";

type ArtifactListProps = {
  generationId: string;
  artifacts: TArtifact[];
};

function formatBytes(size: number): string {
  if (size < 1024) return `${size} B`;
  if (size < 1024 * 1024) return `${(size / 1024).toFixed(1)} KB`;
  return `${(size / 1024 / 1024).toFixed(1)} MB`;
}

export function ArtifactList({ generationId, artifacts }: ArtifactListProps) {
  if (artifacts.length === 0) {
    return <p className="text-sm text-muted-foreground">Artifacts appear when the generation finishes.</p>;
  }
  return (
    <div className="rounded-lg border">
      <Table>
        <TableHeader>
          <TableRow>
            <TableHead>File</TableHead>
            <TableHead>Kind</TableHead>
            <TableHead className="text-right">Size</TableHead>
            <TableHead className="w-12" />
          </TableRow>
        </TableHeader>
        <TableBody>
          {artifacts.map((artifact) => (
            <TableRow key={artifact.artifactId}>
              <TableCell className="font-mono text-xs">{artifact.name}</TableCell>
              <TableCell>
                <Badge variant="outline">{artifact.kind}</Badge>
              </TableCell>
              <TableCell className="text-right text-xs tabular-nums">{formatBytes(artifact.size)}</TableCell>
              <TableCell>
                <a
                  href={artifactUrl(generationId, artifact)}
                  download={artifact.name}
                  aria-label={`Download ${artifact.name}`}
                  className={buttonVariants({ variant: "ghost", size: "icon-sm" })}
                >
                  <Download />
                </a>
              </TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </div>
  );
}
