import type { TPhotoCredit } from "./app";

/** Epic 27: a stock photo's credit over its corner (the parent is `relative`), linked as Unsplash's guidelines ask. */
export function PhotoCredit({ credit }: { credit: TPhotoCredit }) {
  return (
    <span className="absolute right-1.5 bottom-1.5 z-10 max-w-[90%] truncate rounded bg-black/55 px-1.5 py-0.5 text-[10px] leading-4 text-white">
      Photo by{" "}
      <a href={credit.profileUrl} target="_blank" rel="noopener noreferrer" className="underline underline-offset-2" onClick={(event) => event.stopPropagation()}>
        {credit.name}
      </a>{" "}
      on{" "}
      <a href={credit.sourceUrl} target="_blank" rel="noopener noreferrer" className="underline underline-offset-2" onClick={(event) => event.stopPropagation()}>
        Unsplash
      </a>
    </span>
  );
}
