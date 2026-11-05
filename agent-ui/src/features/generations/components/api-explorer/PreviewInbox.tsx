"use client";

import { ExternalLink, Mail } from "lucide-react";
import { Card, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import type { TManifestEmail } from "../../types";

type PreviewInboxProps = {
  email: TManifestEmail;
};

/** Story 10.7: the emails this generation's preview sent, in the shared local mail catcher. */
export function PreviewInbox({ email }: PreviewInboxProps) {
  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2 text-sm">
          <Mail className="size-4" />
          Emails
        </CardTitle>
        <CardDescription className="flex flex-wrap items-center gap-x-2">
          {email.emails.length > 0 ? `Sends ${email.emails.join(", ")}.` : "Sends account emails."}
          <a
            href={email.inbox}
            target="_blank"
            rel="noreferrer"
            className="inline-flex items-center gap-1 font-medium text-primary underline-offset-4 hover:underline"
          >
            Open this preview&apos;s inbox
            <ExternalLink className="size-3" />
          </a>
        </CardDescription>
      </CardHeader>
    </Card>
  );
}
