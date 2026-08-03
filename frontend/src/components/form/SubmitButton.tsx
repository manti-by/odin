import type { ButtonHTMLAttributes } from "react";

interface SubmitButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  label: string;
  variant?: "primary" | "secondary" | "outline";
}

export function SubmitButton({ label, variant = "primary", className, type = "submit", ...rest }: SubmitButtonProps) {
  const cls = [`form__button form__button--${variant}`, className].filter(Boolean).join(" ");
  return (
    <button type={type} className={cls} {...rest}>
      {label}
    </button>
  );
}
