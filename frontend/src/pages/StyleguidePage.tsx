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
  { state: "alive", label: "Alive (success)" },
  { state: "dead", label: "Dead (error)" },
  { state: "heating", label: "Heating (error)" },
  { state: "cooling", label: "Cooling (accent)" },
];

const TOKENS = [
  { name: "--color-bg", value: "#0c0d0e", desc: "Canvas / body background" },
  { name: "--color-surface-1", value: "#0f1011", desc: "Subtle raised surface" },
  { name: "--color-surface-2", value: "#141516", desc: "Cards, panels" },
  { name: "--color-surface-3", value: "#1a1c23", desc: "Modals, dropdowns" },
  { name: "--color-border", value: "#23252a", desc: "Hairline borders, dividers" },
  { name: "--color-border-strong", value: "#34343a", desc: "Input focus borders" },
  { name: "--color-text-primary", value: "#f7f8f8", desc: "Headings, body text" },
  { name: "--color-text-secondary", value: "#8f93a2", desc: "Muted labels, metadata" },
  { name: "--color-text-tertiary", value: "#62666d", desc: "Disabled, footnotes" },
  { name: "--color-accent", value: "#5e6ad2", desc: "Primary buttons, links, focus" },
  { name: "--color-accent-hover", value: "#828fff", desc: "Accent hover" },
  { name: "--color-success", value: "#27a644", desc: "Status pills, success" },
  { name: "--color-error", value: "#ff5370", desc: "Destructive, error states" },
  { name: "--color-warning", value: "#ffcb6b", desc: "Warning banners" },
];

function Swatch({ color }: { color: string }) {
  return (
    <span
      style={{
        display: "inline-block",
        width: 16,
        height: 16,
        borderRadius: 4,
        background: color,
        border: "1px solid var(--color-border)",
        verticalAlign: "middle",
        marginRight: 8,
      }}
    />
  );
}

export function StyleguidePage() {
  const [modalOpen, setModalOpen] = useState(false);
  const [inputValue, setInputValue] = useState("");

  return (
    <section>
      <h2>Styleguide</h2>
      <p>Shared presentational components for the Odin dashboard, themed with the Warp design system.</p>

      <section>
        <h3>Theme tokens</h3>
        <p>
          Dark-first, near-black canvas with a 4-step surface ladder and lavender-blue accent. <code>tokens.css</code>{" "}
          defines all variables consumed by component styles.
        </p>
        <table style={{ width: "100%", borderCollapse: "collapse" }}>
          <thead>
            <tr style={{ borderBottom: "1px solid var(--color-border)" }}>
              <th style={{ textAlign: "left", padding: "0.5rem 0.75rem", fontSize: "0.8rem" }}>Token</th>
              <th style={{ textAlign: "left", padding: "0.5rem 0.75rem", fontSize: "0.8rem" }}>Sample</th>
              <th style={{ textAlign: "left", padding: "0.5rem 0.75rem", fontSize: "0.8rem" }}>Value</th>
              <th style={{ textAlign: "left", padding: "0.5rem 0.75rem", fontSize: "0.8rem" }}>Usage</th>
            </tr>
          </thead>
          <tbody>
            {TOKENS.map((token) => (
              <tr key={token.name} style={{ borderBottom: "1px solid var(--color-border)" }}>
                <td style={{ padding: "0.4rem 0.75rem", fontFamily: "var(--font-mono)", fontSize: "0.8rem" }}>
                  {token.name}
                </td>
                <td style={{ padding: "0.4rem 0.75rem" }}>
                  <Swatch color={token.value} />
                </td>
                <td style={{ padding: "0.4rem 0.75rem", fontFamily: "var(--font-mono)", fontSize: "0.8rem" }}>
                  {token.value}
                </td>
                <td style={{ padding: "0.4rem 0.75rem", fontSize: "0.8rem", color: "var(--color-text-secondary)" }}>
                  {token.desc}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </section>

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
          Data-driven inline sparkline. The default stroke color uses the accent token <code>var(--color-accent)</code>.
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
              color="var(--color-success)"
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
        <p>Surface-2 background, 1px hairline border, title on surface-3. Optional status dot and icon link.</p>
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
        <p>Surface-3 background, hairline border, accent-colored submit button.</p>
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
        <h3>Typography</h3>
        <p>
          UI text uses <code>var(--font-sans)</code>: system-ui, -apple-system, Roboto. Code, IDs, and numeric values
          use <code>var(--font-mono)</code>: JetBrains Mono, Fira Code, SF Mono.
        </p>
        <p style={{ fontFamily: "var(--font-mono)" }}>
          <strong>Monospace sample:</strong> 25.3°C | sensor-esp-01 | 99.7%
        </p>
      </section>

      <section>
        <h3>Container</h3>
        <p>
          The <code>Container</code> component wraps content with the <code>.container</code> class (max-width 1560px)
          and accepts <code>as</code> and <code>fluid</code> props.
        </p>
      </section>
    </section>
  );
}
