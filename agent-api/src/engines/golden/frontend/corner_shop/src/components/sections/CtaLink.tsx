import Link from "next/link";
import { buttonVariants } from "@/components/ui/button";
import { siteConfig } from "@/config/site";

export type TCta = { label: string; page?: string; href?: string };

type CtaLinkProps = {
  cta: TCta;
  variant?: "default" | "outline" | "secondary";
};

/** A call-to-action link: `page` is a FrontendSpec page id, `href` an external URL. */
export function CtaLink({ cta, variant = "default" }: CtaLinkProps) {
  const href = cta.page ? (siteConfig.pages as Record<string, string>)[cta.page] ?? "/" : cta.href ?? "/";
  return (
    <Link href={href} className={buttonVariants({ variant, size: "lg" })}>
      {cta.label}
    </Link>
  );
}
