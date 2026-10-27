const paths: Record<string, string> = {
  shield: "M12 3l7 3v5c0 5-3.5 8.5-7 10-3.5-1.5-7-5-7-10V6l7-3zm-3 9l2 2 4-4",
  clock: "M12 21a9 9 0 100-18 9 9 0 000 18zm0-13v4l3 2",
  pin: "M12 21s-7-6.2-7-11.5A7 7 0 0119 9.5C19 14.8 12 21 12 21zm0-9a2.5 2.5 0 100-5 2.5 2.5 0 000 5z",
  headset: "M4 15v-3a8 8 0 0116 0v3M4 15a2 2 0 002 2h1v-5H6a2 2 0 00-2 2m16 1a2 2 0 01-2 2h-1v-5h1a2 2 0 012 2",
  calendar: "M5 6h14v14H5zM5 10h14M9 3v4m6-4v4M8 14h1m3 0h1m3 0h1M8 17h1m3 0h1",
  home: "M4 11l8-7 8 7v9H4zm6 9v-5h4v5",
  phone: "M5 4h4l2 5-2.5 1.5a11 11 0 005 5L15 13l5 2v4a2 2 0 01-2 2A16 16 0 013 6a2 2 0 012-2",
  mail: "M4 6h16v12H4zm0 0l8 7 8-7",
  arrow: "M5 12h14m-5-5l5 5-5 5",
};

export function Icon({ name, size = 20 }: { name: string; size?: number }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={1.8} strokeLinecap="round" strokeLinejoin="round" aria-hidden>
      <path d={paths[name]} />
    </svg>
  );
}

export function Eyebrow({ children }: { children: React.ReactNode }) {
  return <p className="eyebrow">{children}</p>;
}
