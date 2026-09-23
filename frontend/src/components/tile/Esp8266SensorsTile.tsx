import { Icon } from "@/components/icons/Icon";
import { AliveIndicator } from "@/components/tile/AliveIndicator";
import { HomeIndicatorLink } from "@/components/tile/HomeIndicatorLink";
import { Tile } from "@/components/tile/Tile";
import type { DashboardRelay, DashboardSensor } from "@/lib/api/sensors-dashboard";
import type { ReactNode } from "react";

interface Esp8266SensorsTileProps {
  sensors: DashboardSensor[];
  isAlive?: boolean | null;
  onEditSensor: (sensor: DashboardSensor) => void;
  onEditRelaySchedule: (relay: DashboardRelay) => void;
  loading: boolean;
  error?: string | null;
}

function formatValue(value: string | null): string {
  if (value === null || value === undefined) return "-";
  const num = Number.parseFloat(value);
  if (Number.isNaN(num)) return "-";
  return num.toFixed(1);
}

function relayIndicator(relay: DashboardRelay): ReactNode {
  const tooltip = relay.mode ?? relay.state ?? undefined;
  switch (relay.mode) {
    case "IGNORED":
      return <AliveIndicator state="ignored" title={tooltip} />;
    case "UNKNOWN":
      return <AliveIndicator state="unknown" title={tooltip} />;
  }
  switch (relay.state) {
    case "ON":
      return <Icon name="cooling" alt="cooling" width={20} title={tooltip} />;
    case "OFF":
      return <Icon name="heating" alt="heating" width={20} title={tooltip} />;
    default:
      return <AliveIndicator state="unknown" title={tooltip} />;
  }
}

function canManageSchedule(relay: DashboardRelay): boolean {
  return relay.type === "PUMP" || relay.type === "SERVO";
}

export function Esp8266SensorsTile({ sensors, isAlive, onEditRelaySchedule, loading, error }: Esp8266SensorsTileProps) {
  const status = isAlive == null ? "unknown" : isAlive ? "alive" : "dead";

  const title: ReactNode = (
    <>
      <HomeIndicatorLink href="/admin/sensors/sensor/?type=ESP8266" state={status} />
      {"Sensors"}
    </>
  );

  const iconLink: ReactNode = (
    <a href="/sensors/home" className="graph">
      <Icon name="graph" alt="graph" />
    </a>
  );

  return (
    <Tile title={title} iconLink={iconLink} className="esp8266">
      {loading && sensors.length === 0 ? (
        <p className="tile__loading">Loading...</p>
      ) : error && sensors.length === 0 ? (
        <p className="tile__empty" role="alert">
          {error}
        </p>
      ) : sensors.length === 0 ? (
        <p className="tile__empty">No Data</p>
      ) : (
        <>
          {error && (
            <p className="tile__empty" role="alert">
              {error}
            </p>
          )}
          <ul className="sensor-list">
            {sensors.map((sensor) => {
              const relay = sensor.relay;
              return (
                <li
                  key={sensor.sensor_id}
                  className="sensor-row"
                  data-sensor-id={sensor.sensor_id}
                  data-sensor-name={sensor.name}
                  data-target-temp={String(sensor.context?.target_temp ?? "")}
                >
                  <span className="sensor-row__name">{sensor.name}</span>
                  <span className="sensor-row__relay">
                    {relay ? relayIndicator(relay) : <span className="info">nc</span>}
                  </span>
                  <span className="sensor-row__temp">
                    {formatValue(sensor.temp)}
                    <span>°C</span>
                  </span>
                  <span className="sensor-row__humidity">
                    {formatValue(sensor.humidity)}
                    <span>%</span>
                  </span>
                  {relay && canManageSchedule(relay) && (
                    <span className="sensor-row__edit">
                      <button
                        type="button"
                        className="edit-btn"
                        onClick={() => onEditRelaySchedule(relay)}
                        aria-label="Relay schedule"
                      >
                        <Icon name="settings" alt="schedule" width={20} />
                      </button>
                    </span>
                  )}
                </li>
              );
            })}
          </ul>
        </>
      )}
    </Tile>
  );
}
