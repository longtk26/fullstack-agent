import { siteConfig } from "@/config/site";
import { cn } from "@/lib/utils";

type AssetImageProps = {
  asset: string;
  className?: string;
};

type TAsset = { kind?: string; alt?: string; source?: string };

/** A FrontendSpec asset (`asset:<id>`). Placeholder assets render as a themed panel with the alt text. */
export function AssetImage({ asset, className }: AssetImageProps) {
  const id = asset.replace(/^asset:/, "");
  const meta = (siteConfig.assets as Record<string, TAsset>)[id];
  return (
    <div
      role="img"
      aria-label={meta?.alt ?? id}
      className={cn(
        "aspect-video w-full rounded-xl bg-gradient-to-br from-primary/30 via-accent to-secondary",
        className,
      )}
    />
  );
}

/** A section's `backgroundImage`, filling the section behind its content. */
export function backdropImage(asset?: string) {
  return asset ? <AssetImage asset={asset} className="aspect-auto h-full rounded-none" /> : undefined;
}
