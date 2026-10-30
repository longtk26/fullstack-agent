import { AssetImage } from "@/components/assets/AssetImage";

// The library's sections and custom components import the shared asset renderer from here (Story 15.1).
export { AssetImage };

/** A section's `backgroundImage`, filling the section behind its content. */
export function backdropImage(asset?: string) {
  return asset ? <AssetImage asset={asset} className="aspect-auto h-full rounded-none" /> : undefined;
}
