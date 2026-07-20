import type { ReactNode } from "react";

interface FieldStatusProps {
  tone?: "error" | "info" | "success";
  children: ReactNode;
}

export function FieldStatus({ tone = "error", children }: FieldStatusProps) {
  return (
    <div className={`form__status form__status--${tone}`} role={tone === "error" ? "alert" : "status"}>
      {children}
    </div>
  );
}
