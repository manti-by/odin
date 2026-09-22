import { FieldStatus } from "@/components/form/FieldStatus";
import { Form } from "@/components/form/Form";
import { SelectField } from "@/components/form/SelectField";
import { SubmitButton } from "@/components/form/SubmitButton";
import { TextField } from "@/components/form/TextField";
import { Modal } from "@/components/modal/Modal";
import {
  MAX_SCHEDULE_PERIODS,
  type RelayPeriod,
  type RelayTargetState,
  type RelayType,
  relaysApi,
} from "@/lib/api/relays";
import { type FormEventHandler, useEffect, useRef, useState } from "react";

interface RelayScheduleModalProps {
  open: boolean;
  relayId: string | null;
  relayName: string;
  relayType: RelayType;
  onClose: () => void;
  onSuccess: () => void;
  /** When set, seeds the form from these periods instead of fetching the relay. */
  initialPeriods?: RelayPeriod[];
  /** Optional submit override (used for demos/tests instead of the relay API). */
  onSubmit?: (periods: RelayPeriod[]) => Promise<void>;
}

interface EditablePeriod {
  id: number;
  startTime: string;
  endTime: string;
  targetTemp: string;
  targetState: RelayTargetState;
}

type EditableFields = Omit<EditablePeriod, "id">;

const DEFAULT_START = "08:00";
const DEFAULT_END = "18:00";

// Module-level counter keeps ids unique without mutating a ref during render (Strict Mode safe).
let periodSeq = 0;

function nextPeriodId(): number {
  periodSeq += 1;
  return periodSeq;
}

function createPeriod(overrides: Partial<EditableFields> = {}): EditablePeriod {
  return {
    id: nextPeriodId(),
    startTime: DEFAULT_START,
    endTime: DEFAULT_END,
    targetTemp: "",
    targetState: "ON",
    ...overrides,
  };
}

function toEditable(period: RelayPeriod): EditableFields {
  return {
    startTime: period.start_time ?? "",
    endTime: period.end_time ?? "",
    targetTemp: period.target_temp === null || period.target_temp === undefined ? "" : String(period.target_temp),
    targetState: period.target_state === "OFF" ? "OFF" : "ON",
  };
}

function toPayload(periods: EditablePeriod[], relayType: RelayType): RelayPeriod[] {
  return periods.map((period) => {
    const base = { start_time: period.startTime, end_time: period.endTime };
    return relayType === "SERVO"
      ? { ...base, target_temp: Number(period.targetTemp) }
      : { ...base, target_state: period.targetState };
  });
}

function timeToMinutes(value: string): number | null {
  const match = /^([01]\d|2[0-3]):([0-5]\d)$/.exec(value);
  if (!match) return null;
  return Number(match[1]) * 60 + Number(match[2]);
}

function splitRanges(start: number, end: number): [number, number][] {
  if (start < end) return [[start, end]];
  if (start > end) {
    return [
      [start, 24 * 60],
      [0, end],
    ];
  }
  return [];
}

function validatePeriods(periods: EditablePeriod[], relayType: RelayType): string | null {
  if (periods.length > MAX_SCHEDULE_PERIODS) {
    return `At most ${MAX_SCHEDULE_PERIODS} periods are allowed.`;
  }

  const ranges: [number, number][] = [];
  for (const period of periods) {
    const start = timeToMinutes(period.startTime);
    const end = timeToMinutes(period.endTime);
    if (start === null || end === null) {
      return "Each period needs a valid start and end time.";
    }
    if (start === end) {
      return "Each period needs different start and end times.";
    }
    if (relayType === "SERVO") {
      if (period.targetTemp.trim() === "") {
        return "Each period needs a target temperature.";
      }
      if (Number.isNaN(Number(period.targetTemp))) {
        return "Target temperature must be a number.";
      }
    }
    ranges.push(...splitRanges(start, end));
  }

  for (let i = 0; i < ranges.length; i++) {
    for (let j = i + 1; j < ranges.length; j++) {
      const [startA, endA] = ranges[i];
      const [startB, endB] = ranges[j];
      if (startA < endB && startB < endA) {
        return "Schedule periods must not overlap.";
      }
    }
  }

  return null;
}

export function RelayScheduleModal({
  open,
  relayId,
  relayName,
  relayType,
  onClose,
  onSuccess,
  initialPeriods,
  onSubmit,
}: RelayScheduleModalProps) {
  const [periods, setPeriods] = useState<EditablePeriod[]>([]);
  const [message, setMessage] = useState("");
  const [isError, setIsError] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const timeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const loadRef = useRef({ relayId, initialPeriods });

  // Keep the latest seed inputs available to the open-triggered effect without
  // making them dependencies (parents may pass a fresh `initialPeriods` array each render).
  useEffect(() => {
    loadRef.current = { relayId, initialPeriods };
  });

  useEffect(() => {
    if (timeoutRef.current !== null) {
      clearTimeout(timeoutRef.current);
      timeoutRef.current = null;
    }
    if (!open) {
      return;
    }

    setMessage("");
    setIsError(false);
    setIsSubmitting(false);

    const { relayId: currentRelayId, initialPeriods: seed } = loadRef.current;

    if (seed) {
      setPeriods(seed.length > 0 ? seed.map((period) => createPeriod(toEditable(period))) : [createPeriod()]);
      setIsLoading(false);
      return;
    }

    if (!currentRelayId) {
      setPeriods([]);
      return;
    }

    let active = true;
    setIsLoading(true);
    // Clear any rows from a previously opened relay before the new ones arrive.
    setPeriods([]);

    relaysApi
      .retrieve(currentRelayId)
      .then((relay) => {
        if (!active) return;
        const saved = relay.context?.schedule?.periods ?? [];
        setPeriods(saved.length > 0 ? saved.map((period) => createPeriod(toEditable(period))) : [createPeriod()]);
      })
      .catch(() => {
        if (!active) return;
        setPeriods([]);
        setIsError(true);
        setMessage("Could not load relay schedule.");
      })
      .finally(() => {
        if (active) setIsLoading(false);
      });

    return () => {
      active = false;
      if (timeoutRef.current !== null) {
        clearTimeout(timeoutRef.current);
        timeoutRef.current = null;
      }
    };
  }, [open]);

  const setField = (id: number, patch: Partial<EditablePeriod>) => {
    setPeriods((current) => current.map((period) => (period.id === id ? { ...period, ...patch } : period)));
  };

  const addPeriod = () => {
    if (periods.length >= MAX_SCHEDULE_PERIODS) {
      return;
    }
    const period = createPeriod();
    setPeriods((current) => (current.length >= MAX_SCHEDULE_PERIODS ? current : [...current, period]));
  };

  const removePeriod = (id: number) => {
    setPeriods((current) => current.filter((period) => period.id !== id));
  };

  const handleSubmit: FormEventHandler = async (event) => {
    event.preventDefault();
    if (!relayId && !onSubmit) return;

    const validationError = validatePeriods(periods, relayType);
    if (validationError) {
      setIsError(true);
      setMessage(validationError);
      return;
    }

    if (timeoutRef.current !== null) {
      clearTimeout(timeoutRef.current);
      timeoutRef.current = null;
    }

    setIsSubmitting(true);
    setIsError(false);
    setMessage("Saving...");

    try {
      const payload = toPayload(periods, relayType);
      if (onSubmit) {
        await onSubmit(payload);
      } else if (relayId) {
        await relaysApi.updateContext(relayId, {
          context: { schedule: { periods: payload } },
        });
      }
      onSuccess();
      setMessage("Saved.");
      timeoutRef.current = setTimeout(() => {
        onClose();
      }, 700);
    } catch {
      setIsError(true);
      setMessage("Could not save relay schedule.");
      setIsSubmitting(false);
    }
  };

  const title = relayName ? relayName : "Relay schedule";

  return (
    <Modal open={open} onClose={onClose} title={title}>
      <Form onSubmit={handleSubmit} className="relay-schedule">
        {isLoading ? (
          <p className="relay-schedule__loading">Loading...</p>
        ) : (
          <div className="relay-schedule__periods">
            {periods.map((period) => (
              <div className="period-item" key={period.id}>
                <div className="period-fields">
                  <TextField
                    id={`period-${period.id}-start`}
                    label="Start"
                    type="time"
                    value={period.startTime}
                    onChange={(e) => setField(period.id, { startTime: e.target.value })}
                    required
                  />
                  <TextField
                    id={`period-${period.id}-end`}
                    label="End"
                    type="time"
                    value={period.endTime}
                    onChange={(e) => setField(period.id, { endTime: e.target.value })}
                    required
                  />
                  {relayType === "SERVO" ? (
                    <TextField
                      id={`period-${period.id}-temp`}
                      label="Temperature °C"
                      type="number"
                      step="0.5"
                      value={period.targetTemp}
                      onChange={(e) => setField(period.id, { targetTemp: e.target.value })}
                      required
                    />
                  ) : (
                    <SelectField
                      id={`period-${period.id}-state`}
                      label="Target state"
                      value={period.targetState}
                      onChange={(e) => setField(period.id, { targetState: e.target.value as RelayTargetState })}
                      options={[
                        { value: "ON", label: "ON" },
                        { value: "OFF", label: "OFF" },
                      ]}
                      required
                    />
                  )}
                  <div className="period-item__action">
                    <SubmitButton
                      type="button"
                      label="Remove"
                      variant="secondary"
                      onClick={() => removePeriod(period.id)}
                    />
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}

        <div className="relay-schedule__actions">
          <div className="left-side">
            <SubmitButton
              type="button"
              label="Add period"
              variant="secondary"
              onClick={addPeriod}
              disabled={isLoading || periods.length >= MAX_SCHEDULE_PERIODS}
            />
            <span className="relay-schedule__count">
              {periods.length}/{MAX_SCHEDULE_PERIODS}
            </span>
          </div>
          <div className="right-side">
            <FieldStatus tone={isError ? "error" : "info"}>{message || "\u00A0"}</FieldStatus>
            <SubmitButton label={isSubmitting ? "Saving..." : "Save"} disabled={isSubmitting || isLoading} />
          </div>
        </div>
      </Form>
    </Modal>
  );
}
