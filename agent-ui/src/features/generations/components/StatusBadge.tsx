import { CircleCheck, CircleDashed, CircleX, Ban, Loader2, ShieldCheck, Wrench } from "lucide-react";
import type { LucideIcon } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { cn } from "@/lib/utils";
import type { TGenerationStatus } from "../types";

const STATUS_STYLE: Record<TGenerationStatus, { icon: LucideIcon; className: string; spin?: boolean }> = {
  PENDING: { icon: CircleDashed, className: "bg-muted text-muted-foreground" },
  RUNNING: { icon: Loader2, className: "bg-info/15 text-info", spin: true },
  VALIDATING: { icon: ShieldCheck, className: "bg-info/15 text-info" },
  REPAIRING: { icon: Wrench, className: "bg-warning/20 text-warning-foreground dark:text-warning" },
  COMPLETED: { icon: CircleCheck, className: "bg-success/15 text-success" },
  FAILED: { icon: CircleX, className: "bg-destructive/10 text-destructive" },
  CANCELLED: { icon: Ban, className: "bg-muted text-muted-foreground" },
};

type StatusBadgeProps = {
  status: TGenerationStatus;
  className?: string;
};

export function StatusBadge({ status, className }: StatusBadgeProps) {
  const { icon: Icon, className: tone, spin } = STATUS_STYLE[status] ?? STATUS_STYLE.PENDING;
  return (
    <Badge variant="secondary" className={cn(tone, className)}>
      <Icon className={cn(spin && "animate-spin")} />
      {status.toLowerCase()}
    </Badge>
  );
}
