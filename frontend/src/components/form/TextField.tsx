import type { ChangeEventHandler } from "react";

interface TextFieldProps {
  id: string;
  label: string;
  value: string;
  onChange: ChangeEventHandler<HTMLInputElement>;
  type?: "text" | "number" | "datetime-local";
  name?: string;
  step?: string;
  required?: boolean;
  autoComplete?: string;
}

export function TextField({
  id,
  label,
  value,
  onChange,
  type = "text",
  name,
  step,
  required,
  autoComplete,
}: TextFieldProps) {
  return (
    <div className="form__group">
      <label className="form__label" htmlFor={id}>
        {label}
      </label>
      <input
        className="form__input"
        id={id}
        type={type}
        name={name}
        value={value}
        onChange={onChange}
        step={step}
        required={required}
        autoComplete={autoComplete}
      />
    </div>
  );
}
