import type { ChangeEventHandler } from "react";

export interface SelectOption {
  value: string;
  label: string;
}

interface SelectFieldProps {
  id: string;
  label: string;
  value: string;
  onChange: ChangeEventHandler<HTMLSelectElement>;
  options: SelectOption[];
  name?: string;
  required?: boolean;
}

export function SelectField({ id, label, value, onChange, options, name, required }: SelectFieldProps) {
  return (
    <div className="form__group">
      <label className="form__label" htmlFor={id}>
        {label}
      </label>
      <select className="form__input" id={id} name={name} value={value} onChange={onChange} required={required}>
        {options.map((option) => (
          <option key={option.value} value={option.value}>
            {option.label}
          </option>
        ))}
      </select>
    </div>
  );
}
