import { Icon } from "@/components/icons/Icon";
import { HomeIndicatorLink } from "@/components/tile/HomeIndicatorLink";
import { Tile } from "@/components/tile/Tile";
import type { DashboardSensor } from "@/lib/api/dashboard";
import type { ReactNode } from "react";

interface Esp8266SensorsTileProps {
  sensors: DashboardSensor[];
  isAlive: boolean;
  onEditSensor: (sensor: DashboardSensor) => void;
  loading: boolean;
}

function formatValue(value: string | null): string {
  if (value === null || value === undefined) return "-";
  const num = Number.parseFloat(value);
  if (Number.isNaN(num)) return "-";
  return num.toFixed(1);
}

export function Esp8266SensorsTile({ sensors, isAlive, onEditSensor, loading }: Esp8266SensorsTileProps) {
  const status = isAlive ? "alive" : "dead";

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
    <Tile title={title} iconLink={iconLink}>
      {loading ? (
        <p className="tile__loading">Loading...</p>
      ) : sensors.length === 0 ? (
        <p className="tile__empty">No Data</p>
      ) : (
        <ul className="sensor-list">
          {sensors.map((sensor) => (
            <li
              key={sensor.sensor_id}
              className="sensor-row"
              data-sensor-id={sensor.sensor_id}
              data-sensor-name={sensor.name}
              data-target-temp={String(sensor.context?.target_temp ?? "")}
            >
              <span className="sensor-row__name">{sensor.name}</span>
              <span className="sensor-row__relay">
                {sensor.relay ? (
                  <span
                    className={`alive-indicator alive-indicator--${sensor.relay.is_on ? "heating" : "cooling"}`}
                    aria-label={sensor.relay.is_on ? "heating" : "cooling"}
                  />
                ) : (
                  <span className="info">nc</span>
                )}
              </span>
              <span className="sensor-row__temp">
                {formatValue(sensor.temp)}
                <span>°C</span>
              </span>
              <span className="sensor-row__humidity">
                {formatValue(sensor.humidity)}
                <span>%</span>
              </span>
              <span className="sensor-row__edit">
                <button type="button" className="edit-btn" onClick={() => onEditSensor(sensor)} aria-label="Edit">
                  <Icon name="settings" alt="settings" width={20} />
                </button>
              </span>
            </li>
          ))}
        </ul>
      )}
    </Tile>
  );
}
