import { Filter, Search, X } from "lucide-react";
import { Button } from "@/components/ui/button";
import {
  DropdownMenu,
  DropdownMenuCheckboxItem,
  DropdownMenuContent,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Switch } from "@/components/ui/switch";
import { KIND_STYLE } from "../../lib/span-style";
import { SPAN_KINDS, type TTraceFilters } from "../../lib/trace-tree";

type TraceFiltersProps = {
  filters: TTraceFilters;
  lanes: string[];
  onChange: (patch: Partial<TTraceFilters>) => void;
  onReset: () => void;
};

const SLOWEST = [
  { value: "all", label: "All spans" },
  { value: "10", label: "Slowest 10" },
  { value: "25", label: "Slowest 25" },
  { value: "50", label: "Slowest 50" },
];

/** One row above the waterfall: kinds, lane, errors only, slowest N, search by name or path. */
export function TraceFilters({ filters, lanes, onChange, onReset }: TraceFiltersProps) {
  const kindsLabel = filters.kinds.length === SPAN_KINDS.length ? "All kinds" : `${filters.kinds.length} kinds`;
  return (
    <div className="flex flex-wrap items-center gap-2">
      <div className="relative w-full sm:w-64">
        <Search className="pointer-events-none absolute top-1/2 left-2 size-4 -translate-y-1/2 text-muted-foreground" />
        <Input
          value={filters.search}
          onChange={(event) => onChange({ search: event.target.value })}
          placeholder="Search name or path"
          className="pl-8"
          aria-label="Search spans"
        />
      </div>
      <DropdownMenu>
        <DropdownMenuTrigger render={<Button variant="outline" size="sm" />}>
          <Filter /> {kindsLabel}
        </DropdownMenuTrigger>
        <DropdownMenuContent>
          {SPAN_KINDS.map((kind) => (
            <DropdownMenuCheckboxItem
              key={kind}
              checked={filters.kinds.includes(kind)}
              onCheckedChange={(checked) =>
                onChange({
                  kinds: checked ? [...filters.kinds, kind] : filters.kinds.filter((value) => value !== kind),
                })
              }
            >
              <span className={`size-2 rounded-full ${KIND_STYLE[kind].dot}`} />
              {KIND_STYLE[kind].label}
            </DropdownMenuCheckboxItem>
          ))}
        </DropdownMenuContent>
      </DropdownMenu>
      {lanes.length > 1 && (
        <Select
          items={[{ value: "all", label: "All lanes" }, ...lanes.map((lane) => ({ value: lane, label: lane }))]}
          value={filters.lane ?? "all"}
          onValueChange={(value) => onChange({ lane: value === "all" ? null : String(value) })}
        >
          <SelectTrigger size="sm" className="w-32" aria-label="Lane">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">All lanes</SelectItem>
            {lanes.map((lane) => (
              <SelectItem key={lane} value={lane}>
                {lane}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      )}
      <Select
        items={SLOWEST}
        value={filters.slowest == null ? "all" : String(filters.slowest)}
        onValueChange={(value) => onChange({ slowest: value === "all" ? null : Number(value) })}
      >
        <SelectTrigger size="sm" className="w-36" aria-label="Slowest spans">
          <SelectValue />
        </SelectTrigger>
        <SelectContent>
          {SLOWEST.map((option) => (
            <SelectItem key={option.value} value={option.value}>
              {option.label}
            </SelectItem>
          ))}
        </SelectContent>
      </Select>
      <div className="flex items-center gap-2 px-1">
        <Switch
          id="trace-errors-only"
          checked={filters.errorsOnly}
          onCheckedChange={(checked) => onChange({ errorsOnly: checked })}
        />
        <Label htmlFor="trace-errors-only" className="text-sm font-normal">
          Errors only
        </Label>
      </div>
      <Button variant="ghost" size="sm" onClick={onReset}>
        <X /> Reset
      </Button>
    </div>
  );
}
