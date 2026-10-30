// Generated from src/assets/svg/work-1.svg by the Fullstack Generation Agent. Do not edit:
// change the SVG (or the FrontendSpec asset) and regenerate.
export default function Work1Asset({ className }: { className?: string }) {
  return (
    <svg viewBox="0 0 1600 900" className={className} role="img" aria-label="Bakehouse packaging">
      <title>{"Bakehouse packaging"}</title>
      <defs>
        <linearGradient id="work-1-shade" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0" stopColor="var(--secondary)" />
          <stop offset="1" stopColor="var(--muted)" />
        </linearGradient>
      </defs>
      <rect width="1600" height="900" fill="url(#work-1-shade)" />
      <rect x="0" y="700" width="1600" height="200" fill="var(--foreground)" opacity="0.08" />
      <g id="work-1-bag">
        <path d="M420 250 L760 250 L800 720 L380 720 Z" fill="var(--background)" stroke="var(--foreground)" strokeOpacity="0.25" strokeWidth="4" />
        <path d="M420 250 L470 200 L710 200 L760 250 Z" fill="var(--muted)" />
        <path d="M590 380 C 560 440 560 520 590 580 C 620 520 620 440 590 380 Z" fill="var(--accent)" />
        <path d="M590 600 L590 380" stroke="var(--primary)" strokeWidth="8" strokeLinecap="round" />
      </g>
      <g id="work-1-box">
        <rect x="900" y="420" width="380" height="300" rx="8" fill="var(--primary)" />
        <rect x="900" y="380" width="380" height="70" rx="8" fill="var(--accent)" />
        <circle cx="1090" cy="570" r="64" fill="none" stroke="var(--primary-foreground)" strokeWidth="8" />
        <path d="M1090 520 L1090 620 M1062 545 L1090 575 L1118 545" fill="none" stroke="var(--primary-foreground)" strokeWidth="8" strokeLinecap="round" />
      </g>
    </svg>
  );
}
