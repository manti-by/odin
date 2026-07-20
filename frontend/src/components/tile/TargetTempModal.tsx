import { FieldStatus } from "@/components/form/FieldStatus";
import { Form } from "@/components/form/Form";
import { SubmitButton } from "@/components/form/SubmitButton";
import { TextField } from "@/components/form/TextField";
import { Modal } from "@/components/modal/Modal";
import type { DashboardSensor } from "@/lib/api/dashboard";
import { sensorsApi } from "@/lib/api/sensors";
import { type FormEventHandler, useEffect, useRef, useState } from "react";

interface TargetTempModalProps {
  open: boolean;
  sensor: DashboardSensor | null;
  onClose: () => void;
  onSuccess: () => void;
}

export function TargetTempModal({ open, sensor, onClose, onSuccess }: TargetTempModalProps) {
  const [temp, setTemp] = useState("");
  const [message, setMessage] = useState("");
  const [isError, setIsError] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const timeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  useEffect(() => {
    if (timeoutRef.current !== null) {
      clearTimeout(timeoutRef.current);
      timeoutRef.current = null;
    }
    if (open && sensor) {
      const targetTemp = sensor.context?.target_temp;
      setTemp(typeof targetTemp === "string" ? targetTemp : "");
      setMessage("");
      setIsError(false);
    }
    return () => {
      if (timeoutRef.current !== null) {
        clearTimeout(timeoutRef.current);
        timeoutRef.current = null;
      }
    };
  }, [open, sensor]);

  const handleSubmit: FormEventHandler = async (event) => {
    event.preventDefault();
    if (!sensor || temp === "") {
      setMessage("Target temperature is required.");
      setIsError(true);
      return;
    }

    if (timeoutRef.current !== null) {
      clearTimeout(timeoutRef.current);
      timeoutRef.current = null;
    }

    setIsSubmitting(true);
    setMessage("Saving...");
    setIsError(false);

    try {
      await sensorsApi.update(sensor.sensor_id, { context: { ...sensor.context, target_temp: temp } });
      onSuccess();
      setMessage("Saved.");
      setIsError(false);
      timeoutRef.current = setTimeout(() => {
        onClose();
      }, 700);
    } catch {
      setMessage("Could not save target temperature.");
      setIsError(true);
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <Modal open={open} onClose={onClose} title="Set temp">
      <Form onSubmit={handleSubmit}>
        <TextField
          id="target-temp-input"
          label="Temperature °C"
          type="number"
          step="0.5"
          value={temp}
          onChange={(e) => setTemp(e.target.value)}
          required
          autoComplete="off"
        />
        <FieldStatus tone={isError ? "error" : "info"}>{message || "\u00A0"}</FieldStatus>
        <SubmitButton label={isSubmitting ? "Saving..." : "Send"} disabled={isSubmitting} />
      </Form>
    </Modal>
  );
}
