import { MiniSparkline } from "@/components/chart/MiniSparkline";
import { FieldStatus } from "@/components/form/FieldStatus";
import { Form } from "@/components/form/Form";
import { SubmitButton } from "@/components/form/SubmitButton";
import { TextField } from "@/components/form/TextField";
import { ResponsiveGrid } from "@/components/grid/ResponsiveGrid";
import { Icon } from "@/components/icons/Icon";
import { Modal } from "@/components/modal/Modal";
import { AliveIndicator } from "@/components/tile/AliveIndicator";
import type { AliveState } from "@/components/tile/AliveIndicator";
import { Tile } from "@/components/tile/Tile";
import { useState } from "react";

const ALIVE_STATES: { state: AliveState; label: string }[] = [
  { state: "alive", label: "Alive (#4caf50)" },
  { state: "dead", label: "Dead (#f44336)" },
  { state: "heating", label: "Heating (#f44336)" },
  { state: "cooling", label: "Cooling (#007190)" },
];

export function StyleguidePage() {
  const [modalOpen, setModalOpen] = useState(false);
  const [inputValue, setInputValue] = useState("");

  return (
    <section>
      <h2>Styleguide</h2>
      <p>Shared presentational components for the Odin dashboard.</p>

      <section>
        <h3>AliveIndicator</h3>
        <p>Four states rendered inline:</p>
        <p>
          {ALIVE_STATES.map(({ state, label }) => (
            <span
              key={state}
              style={{ marginRight: "1rem", display: "inline-flex", alignItems: "center", gap: "0.35rem" }}
            >
              <AliveIndicator state={state} />
              <span>{label}</span>
            </span>
          ))}
        </p>
      </section>

      <section>
        <h3>Icon</h3>
        <p style={{ display: "flex", gap: "1rem", alignItems: "center" }}>
          <Icon name="graph" alt="graph" />
          <Icon name="settings" alt="settings" width={20} />
          <Icon name="cooling" alt="cooling" width={20} />
          <Icon name="heating" alt="heating" width={20} />
        </p>
      </section>

      <section>
        <h3>MiniSparkline</h3>
        <p>
          Data-driven inline sparkline. Replaces the server-rendered gauge <code>{"<img>"}</code>. Renders from JSON
          data (no server round-trip for chart rendering).
        </p>
        <div style={{ display: "flex", gap: "2rem", alignItems: "center", flexWrap: "wrap" }}>
          <div style={{ width: 120 }}>
            <MiniSparkline
              points={[
                { timestamp: "2026-07-20T10:00:00", value: 22 },
                { timestamp: "2026-07-20T11:00:00", value: 23 },
                { timestamp: "2026-07-20T12:00:00", value: 25 },
                { timestamp: "2026-07-20T13:00:00", value: 24 },
                { timestamp: "2026-07-20T14:00:00", value: 27 },
              ]}
            />
          </div>
          <div style={{ width: 120 }}>
            <MiniSparkline
              color="rgba(255, 99, 132, 1)"
              points={[
                { timestamp: "2026-07-20T10:00:00", value: 30 },
                { timestamp: "2026-07-20T11:00:00", value: 28 },
                { timestamp: "2026-07-20T12:00:00", value: 26 },
                { timestamp: "2026-07-20T13:00:00", value: 24 },
                { timestamp: "2026-07-20T14:00:00", value: 22 },
              ]}
            />
          </div>
        </div>
      </section>

      <section>
        <h3>Tile</h3>
        <p>Tiles with title, optional status dot, optional icon link, and body slot:</p>
        <ResponsiveGrid>
          <Tile
            title="Sensors"
            status="alive"
            iconLink={
              <a href="/styleguide">
                <Icon name="graph" alt="graph" />
              </a>
            }
          >
            <p>Tile body content goes here. This tile has status=alive and a graph icon link.</p>
          </Tile>

          <Tile
            title="Boiler Room"
            status="dead"
            iconLink={
              <a href="/styleguide">
                <Icon name="graph" alt="graph" />
              </a>
            }
          >
            <p>Tile body content. This tile has status=dead and a graph icon link.</p>
          </Tile>

          <Tile title="Weather">
            <p>Tile without status indicator or icon link.</p>
          </Tile>
        </ResponsiveGrid>
      </section>

      <section>
        <h3>Modal</h3>
        <SubmitButton label="Open modal" variant="primary" onClick={() => setModalOpen(true)} />
        <Modal
          open={modalOpen}
          onClose={() => setModalOpen(false)}
          title="Set temperature"
          message={inputValue ? `Sending ${inputValue}°C…` : undefined}
        >
          <Form
            onSubmit={(e) => {
              e.preventDefault();
            }}
          >
            <input type="hidden" name="sensor_id" value="sensor-1" />
            <TextField
              id="modal-temp-input"
              label="Temperature °C"
              type="number"
              name="target_temp"
              value={inputValue}
              onChange={(e) => setInputValue(e.target.value)}
              step="0.5"
              required
            />
            <SubmitButton label="Send" variant="primary" />
          </Form>
        </Modal>
      </section>

      <section>
        <h3>Form primitives</h3>
        <Form
          onSubmit={(e) => {
            e.preventDefault();
          }}
        >
          <TextField
            id="demo-text"
            label="Text input"
            value={inputValue}
            onChange={(e) => setInputValue(e.target.value)}
          />
          <TextField
            id="demo-number"
            label="Number input"
            type="number"
            value={inputValue}
            onChange={(e) => setInputValue(e.target.value)}
            step="0.5"
          />
          <SubmitButton label="Primary" variant="primary" />
          <SubmitButton label="Secondary" variant="secondary" />
          <SubmitButton label="Outline" variant="outline" />
          <SubmitButton label="Disabled" variant="primary" disabled />
          <FieldStatus tone="error">Error message (required field)</FieldStatus>
          <FieldStatus tone="info">Info message</FieldStatus>
          <FieldStatus tone="success">Success message</FieldStatus>
        </Form>
      </section>

      <section>
        <h3>Container</h3>
        <p>
          The <code>Container</code> component is used to wrap content. It renders the <code>.container</code> class
          (max-width 1560px) and accepts <code>as</code> and <code>fluid</code> props.
        </p>
      </section>
    </section>
  );
}
