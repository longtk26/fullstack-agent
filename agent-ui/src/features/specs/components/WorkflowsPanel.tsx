import { Route } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import type { TDraftBusiness } from "../types";

/** Epic 26 (26.1, 26.2): the business workflows the draft was built around and what must be true at each step,
 *  written down before anything is generated. Read-only: the app is evaluated against them after generation. */
export function WorkflowsPanel({ business }: { business: TDraftBusiness }) {
  const data = business.business;
  if (!data?.workflows?.length) {
    return business.error ? (
      <Card>
        <CardHeader>
          <CardTitle>Business workflows</CardTitle>
          <CardDescription>{business.error}</CardDescription>
        </CardHeader>
      </Card>
    ) : null;
  }
  const actors = new Map((data.actors ?? []).map((actor) => [actor.id, actor.name]));
  const golden = data.scope?.goldenPath;
  const ordered = [...data.workflows].sort((a, b) => Number(a.priority === "later") - Number(b.priority === "later"));
  return (
    <Card data-bga-workflows>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <Route className="size-4" /> Business workflows
        </CardTitle>
        <CardDescription>
          Found in the requirement before drafting; the app is checked against them after it is generated.
        </CardDescription>
      </CardHeader>
      <CardContent className="flex flex-col gap-5 text-sm">
        {ordered.map((workflow) => {
          const texts = (business.texts ?? []).filter((item) => item.workflow === workflow.id && item.path === "main");
          return (
            <section key={workflow.id} className="flex flex-col gap-2">
              <h3 className="flex flex-wrap items-center gap-2 font-medium">
                {workflow.name}
                {workflow.id === golden && <Badge>Most important</Badge>}
                {workflow.priority === "later" && <Badge variant="outline">Later</Badge>}
              </h3>
              {workflow.trigger && <p className="text-muted-foreground">Starts when: {workflow.trigger}</p>}
              <ol className="list-decimal pl-5">
                {workflow.steps.map((step) => {
                  const expectations = texts.find((item) => item.step === step.id)?.texts ?? [];
                  return (
                    <li key={step.id}>
                      <span className="font-medium">{actors.get(step.actor) ?? step.actor}</span>: {step.action}
                      {step.statusAfter ? ` → ${step.statusAfter}` : ""}
                      {step.rule ? <span className="text-muted-foreground"> (rule: {step.rule})</span> : null}
                      {expectations.length > 0 && (
                        <ul className="mt-1 list-disc pl-5 text-xs text-muted-foreground">
                          {expectations.map((text, index) => (
                            <li key={index}>{text}</li>
                          ))}
                        </ul>
                      )}
                    </li>
                  );
                })}
              </ol>
              {(workflow.branches ?? []).map((branch) => (
                <p key={branch.id} className="pl-5 text-muted-foreground">
                  If {branch.condition}: {branch.steps.map((step) => step.action).join(", then ")}
                </p>
              ))}
              {workflow.outcome && <p className="text-muted-foreground">Done when: {workflow.outcome}</p>}
            </section>
          );
        })}
        {(business.binding?.problems?.length ?? 0) > 0 && (
          <p className="text-muted-foreground">
            {business.binding?.problems?.length} step(s) could not be bound to the app; the Business tab lists them.
          </p>
        )}
      </CardContent>
    </Card>
  );
}
