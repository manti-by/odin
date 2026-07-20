import type { ElementType, ReactNode } from "react";

interface ContainerProps {
  as?: ElementType;
  fluid?: boolean;
  className?: string;
  children: ReactNode;
}

export function Container({ as: As = "div", fluid = false, className, children }: ContainerProps) {
  const cls = ["container", fluid && "container--fluid", className].filter(Boolean).join(" ");
  return <As className={cls}>{children}</As>;
}
