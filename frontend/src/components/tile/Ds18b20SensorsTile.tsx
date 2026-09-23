import { Icon } from "@/components/icons/Icon";
import { HomeIndicatorLink } from "@/components/tile/HomeIndicatorLink";
import { Tile } from "@/components/tile/Tile";
import type { DashboardSensor } from "@/lib/api/sensors-dashboard";
import type { ReactNode } from "react";

interface Ds18b20SensorsTileProps {
  sensors: DashboardSensor[];
  isAlive: boolean;
  loading: boolean;
  error?: string | null;
}

function formatLinkedTemp(value: string | null): string {
  if (value === null) return "-\u00B0C";
  const num = Number.parseFloat(value);
  return Number.isNaN(num) ? "-\u00B0C" : `${num.toFixed(1)}\u00B0C`;
}

export function Ds18b20SensorsTile({ sensors, isAlive, loading, error }: Ds18b20SensorsTileProps) {
  const status = isAlive ? "alive" : "dead";

  const title: ReactNode = (
    <>
      <HomeIndicatorLink href="/admin/sensors/sensor/?type=DS18B20" state={status} />
      {"Boiler Room"}
    </>
  );

  const iconLink: ReactNode = (
    <a href="/sensors/boiler" className="graph">
      <Icon name="graph" alt="graph" />
    </a>
  );

  return (
    <Tile title={title} iconLink={iconLink}>
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
          <ul className="sensor-row-group">
            {sensors.map((sensor) => (
              <li key={sensor.sensor_id} className="sensor-card">
                <div className="sensor-card__value">
                  <img
                    src={`/api/v1/core/chart/?value=${encodeURIComponent(sensor.temp ?? "")}&metric=temp`}
                    alt={`${sensor.name} chart`}
                  />
                </div>
                <div className="sensor-card__attrs">
                  {sensor.relay && (
                    <span className="sensor-card__relay">
                      <Icon
                        name={sensor.relay.is_on ? "heating" : "cooling"}
                        alt={sensor.relay.is_on ? "heating" : "cooling"}
                        width={24}
                      />
                    </span>
                  )}
                  {sensor.linked_sensor && (
                    <span className="linked-sensor">
                      <span className="linked-sensor__arrow">⊙</span>
                      {formatLinkedTemp(sensor.linked_sensor.temp)}
                    </span>
                  )}
                </div>
                <div className="sensor-card__name">{sensor.name}</div>
              </li>
            ))}
          </ul>
        </>
      )}
    </Tile>
  );
}
