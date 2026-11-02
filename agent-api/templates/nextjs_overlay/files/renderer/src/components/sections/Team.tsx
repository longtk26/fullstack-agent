import { Grid } from "@/components/layout/Grid";
import { Section } from "@/components/layout/Section";
import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import { cn } from "@/lib/utils";
import { AssetImage, backdropImage } from "./AssetImage";
import type { TTeamContent } from "./types";

type TeamProps = TTeamContent;
type TMember = NonNullable<TeamProps["items"]>[number];

const initials = (name: string) =>
  name
    .split(/\s+/)
    .slice(0, 2)
    .map((part) => part[0] ?? "")
    .join("");

function Face({ member, large = false }: { member: TMember; large?: boolean }) {
  if (member.image) {
    return <AssetImage asset={member.image} className={large ? "aspect-[3/4]" : "size-16 shrink-0 rounded-full"} />;
  }
  return (
    <Avatar className={cn("shrink-0", large ? "aspect-[3/4] h-auto w-full rounded-xl" : "size-16")}>
      <AvatarFallback className={cn(large && "rounded-xl text-2xl")}>{initials(member.name)}</AvatarFallback>
    </Avatar>
  );
}

function Who({ member }: { member: TMember }) {
  return (
    <div className="flex flex-col gap-1">
      <h3 className="text-lg font-semibold">{member.name}</h3>
      {member.role && <p className="text-sm text-primary">{member.role}</p>}
      {member.bio && <p className="max-w-prose text-muted-foreground">{member.bio}</p>}
    </div>
  );
}

/**
 * The people (Story 20.8), in three forms: `grid` (face and name in a grid), `list` (rows with the bio beside) and
 * `portraits` (large portrait images). Without a photo a member shows their initials.
 */
export function Team({ title, description, items = [], form = "grid", background, backgroundImage }: TeamProps) {
  return (
    <Section title={title} description={description} background={background} backdrop={backdropImage(backgroundImage)}>
      {form === "list" ? (
        <ul className="flex flex-col divide-y divide-border">
          {items.map((member) => (
            <li key={member.name} className="flex gap-5 py-6 first:pt-0">
              <Face member={member} />
              <Who member={member} />
            </li>
          ))}
        </ul>
      ) : (
        <Grid columns={form === "portraits" ? 3 : items.length >= 4 ? 4 : 3}>
          {items.map((member) => (
            <div key={member.name} className={cn("flex flex-col gap-4", form === "grid" && "items-start")}>
              <Face member={member} large={form === "portraits"} />
              <Who member={member} />
            </div>
          ))}
        </Grid>
      )}
    </Section>
  );
}
