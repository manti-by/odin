import type { ReactNode } from "react";

interface ResponsiveGridProps {
  children: ReactNode;
  className?: string;
}

export function ResponsiveGrid({ children, className }: ResponsiveGridProps) {
  const cls = ["grid", className].filter(Boolean).join(" ");
  return <div className={cls}>{children}</div>;
}
