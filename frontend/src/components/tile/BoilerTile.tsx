import { Tile } from "@/components/tile/Tile";
import type { BoilerMode, BoilerStatus } from "@/lib/api/boiler";

interface BoilerTileProps {
  status: BoilerStatus | null;
  loading: boolean;
  error: string | null;
}

const MODE_LABELS: Record<BoilerMode, string> = {
  heating: "Heating",
  mixed: "Mixed",
  off: "Off",
  boiling: "Boiling",
  clear_override: "Clear override",
};

const WEEKDAYS = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"];

function formatTemp(value: number | null): string {
  return value === null ? "—" : `${value}°C`;
}

function formatUpdated(value: string | null): string {
  if (!value) return "—";
  const d = new Date(value);
  if (Number.isNaN(d.getTime())) return "—";
  const day = String(d.getDate()).padStart(2, "0");
  const month = String(d.getMonth() + 1).padStart(2, "0");
  const hours = String(d.getHours()).padStart(2, "0");
  const minutes = String(d.getMinutes()).padStart(2, "0");
  return `${day}.${month} ${hours}:${minutes}`;
}

function formatSchedule(value: string | null): string {
  if (!value) return "—";
  const d = new Date(value);
  if (Number.isNaN(d.getTime())) return "—";
  const hours = String(d.getHours()).padStart(2, "0");
  const minutes = String(d.getMinutes()).padStart(2, "0");
  return `${WEEKDAYS[d.getDay()]} ${hours}:${minutes}`;
}

export function BoilerTile({ status, loading, error }: BoilerTileProps) {
  const aliveState = status ? (status.ebusd_alive ? "alive" : "dead") : undefined;

  return (
    <Tile title="Boiler" status={aliveState} className="boiler">
      {loading && !status ? (
        <p className="tile__loading">Loading...</p>
      ) : error && !status ? (
        <p className="tile__empty" role="alert">
          {error}
        </p>
      ) : !status ? (
        <p className="tile__empty">No Data</p>
      ) : (
        <>
          <div className="boiler-mode">
            <span className="boiler-mode__value">
              {status.mode ? (MODE_LABELS[status.mode] ?? status.mode) : "—"}
            </span>
            <span className={`boiler-override boiler-override--${status.override_active ? "on" : "off"}`}>
              {status.override_active ? "Override" : "Panel"}
            </span>
          </div>
          <div className="boiler-temps">
            <div className="boiler-temps__item">
              <span className="boiler-temps__label">Flow</span>
              <span className="boiler-temps__value">{formatTemp(status.target_temp)}</span>
            </div>
            <div className="boiler-temps__item">
              <span className="boiler-temps__label">Hot water</span>
              <span className="boiler-temps__value">{formatTemp(status.hwc_temp)}</span>
            </div>
          </div>
          <div className="boiler-rows">
            <div className="boiler-row">
              <span className="boiler-row__label">Updated</span>
              <span className="boiler-row__value">{formatUpdated(status.override_updated_at)}</span>
            </div>
            <div className="boiler-row">
              <span className="boiler-row__label">Next boil</span>
              <span className="boiler-row__value">{formatSchedule(status.next_boil_at)} · 55°C</span>
            </div>
            <div className="boiler-row">
              <span className="boiler-row__label">Clear</span>
              <span className="boiler-row__value">{formatSchedule(status.next_clear_at)}</span>
            </div>
          </div>
          {!status.ebusd_alive && <p className="boiler-offline">eBus offline</p>}
        </>
      )}
    </Tile>
  );
}
