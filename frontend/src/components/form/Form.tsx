import type { FormEventHandler, ReactNode } from "react";

interface FormProps {
  onSubmit: FormEventHandler<HTMLFormElement>;
  children: ReactNode;
  className?: string;
}

export function Form({ onSubmit, children, className }: FormProps) {
  const cls = ["form", className].filter(Boolean).join(" ");
  return (
    <form className={cls} onSubmit={onSubmit}>
      {children}
    </form>
  );
}
