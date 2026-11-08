import { assets } from "@/assets";
import { cn } from "@/lib/utils";

const RATIOS: Record<string, string> = {
  "16:9": "aspect-video",
  "4:3": "aspect-[4/3]",
  "1:1": "aspect-square",
  "3:4": "aspect-[3/4]",
  "21:9": "aspect-[21/9]",
};

type AssetImageProps = {
  asset: string;
  className?: string;
  /** Above the fold: load right away instead of lazily. */
  priority?: boolean;
};

/**
 * A FrontendSpec asset (`asset:<id>`, Story 15.1) from the generated registry (`src/assets/index.ts`): a drawn SVG
 * component, an uploaded file, a linked image, a lucide icon, or a themed placeholder panel with the alt text.
 * `data-bga-asset` lets the checks find each asset on its page.
 */
export function AssetImage({ asset, className, priority = false }: AssetImageProps) {
  const id = asset.replace(/^asset:/, "");
  const entry = assets[id];
  const decorative = entry?.decorative ?? false;
  const label = decorative ? undefined : (entry?.alt ?? id);
  const frame = cn("relative w-full overflow-hidden rounded-xl", RATIOS[entry?.aspectRatio ?? "16:9"], className);

  if (entry?.mode === "icon" && entry.component) {
    const Icon = entry.component;
    return (
      <span
        data-bga-asset={id}
        role={label ? "img" : undefined}
        aria-label={label}
        aria-hidden={decorative || undefined}
        className={cn("inline-flex size-6", className)}
      >
        <Icon className="size-full" />
      </span>
    );
  }
  if (entry?.mode === "svg-component" && entry.component) {
    const Drawing = entry.component;
    return (
      <div data-bga-asset={id} className={frame}>
        <Drawing className="size-full" />
      </div>
    );
  }
  if ((entry?.mode === "public-file" || entry?.mode === "remote") && entry.src) {
    return (
      <div data-bga-asset={id} className={frame}>
        {/* eslint-disable-next-line @next/next/no-img-element -- static export: images are served as they are */}
        <img
          src={entry.src}
          alt={label ?? ""}
          aria-hidden={decorative || undefined}
          width={entry.width}
          height={entry.height}
          loading={priority ? "eager" : "lazy"}
          referrerPolicy={entry.mode === "remote" ? "no-referrer" : undefined}
          className="size-full object-cover"
        />
        {creditOf(entry) && <PhotoCredit credit={creditOf(entry)!} />}
      </div>
    );
  }
  // Story 19.4: runtime https:// URLs and site paths (/assets/...)
  const isHttps = asset.startsWith("https://");
  const isSitePath = asset.startsWith("/assets/");
  if (!entry && (isHttps || isSitePath)) {
    return (
      <div data-bga-asset={asset} className={frame}>
        {/* eslint-disable-next-line @next/next/no-img-element */}
        <img
          src={asset}
          alt=""
          loading={priority ? "eager" : "lazy"}
          referrerPolicy={isHttps ? "no-referrer" : undefined}
          className="size-full object-cover"
        />
      </div>
    );
  }
  return (
    <div
      data-bga-asset={id}
      role={label ? "img" : undefined}
      aria-label={label}
      aria-hidden={decorative || undefined}
      className={cn(frame, "bg-gradient-to-br from-primary/30 via-accent to-secondary")}
    />
  );
}

type TCredit = { name: string; profileUrl: string; sourceUrl: string };

/** Epic 27: a registry declares `credit` only when a photo has one, so it is read without the type. */
function creditOf(entry: object): TCredit | undefined {
  return (entry as { credit?: TCredit }).credit;
}

/** Epic 27: a stock photo's credit, over its corner, linked as Unsplash's guidelines ask. */
function PhotoCredit({ credit }: { credit: TCredit }) {
  return (
    <span className="absolute right-1.5 bottom-1.5 max-w-[90%] truncate rounded bg-black/55 px-1.5 py-0.5 text-[10px] leading-4 text-white">
      Photo by{" "}
      <a href={credit.profileUrl} target="_blank" rel="noopener noreferrer" className="underline underline-offset-2">
        {credit.name}
      </a>{" "}
      on{" "}
      <a href={credit.sourceUrl} target="_blank" rel="noopener noreferrer" className="underline underline-offset-2">
        Unsplash
      </a>
    </span>
  );
}
