import { Tile } from "@/components/tile/Tile";
import type { ErrorLogEntry, TrafficData, VoltageData } from "@/lib/api/dashboard";

interface SystemErrorsTileProps {
  traffic: TrafficData | null;
  voltage: VoltageData | null;
  systemdStatus: Record<string, { status?: string; error?: string }>;
  errorLogs: ErrorLogEntry[];
  loading: boolean;
}

function formatLogTime(asctime: string): string {
  const match = asctime.match(/^(\d{4})-(\d{2})-(\d{2})[T ](\d{2}):(\d{2})/);
  if (match) {
    return `${match[3]}.${match[2]} ${match[4]}:${match[5]}`;
  }
  const d = new Date(asctime);
  if (!Number.isNaN(d.getTime())) {
    const day = String(d.getDate()).padStart(2, "0");
    const month = String(d.getMonth() + 1).padStart(2, "0");
    const hours = String(d.getHours()).padStart(2, "0");
    const minutes = String(d.getMinutes()).padStart(2, "0");
    return `${day}.${month} ${hours}:${minutes}`;
  }
  return asctime;
}

function formatVoltage(value: string): string {
  const num = Number.parseFloat(value);
  if (Number.isNaN(num)) return "-";
  return Math.round(num).toString();
}

export function SystemErrorsTile({ voltage, systemdStatus, errorLogs, loading }: SystemErrorsTileProps) {
  const systemdEntries = Object.entries(systemdStatus);

  return (
    <Tile title="Other">
      {loading ? (
        <p className="tile__loading">Loading...</p>
      ) : (
        <>
          {voltage && (
            <div className="system-voltage">
              <span className="label">Voltage</span>
              <span className="value">{formatVoltage(voltage.voltage)} V</span>
            </div>
          )}
          <div className="system-systemd">
            {systemdEntries.length > 0 ? (
              <ul>
                {systemdEntries.map(([service, status]) => (
                  <li key={service} className="systemd-entry">
                    <span className="systemd-entry__service">{service}</span>
                    {status.error ? (
                      <span className="systemd-entry__error">{status.error}</span>
                    ) : (
                      <span className="systemd-entry__status">{status.status}</span>
                    )}
                  </li>
                ))}
              </ul>
            ) : (
              <div className="success info">No errors for the last 24 hours</div>
            )}
          </div>
          <div className="system-errors">
            {errorLogs.length > 0 ? (
              <ul>
                {errorLogs.map((log, i) => (
                  <li key={`${log.asctime}-${log.msg}-${i}`} className="log-entry">
                    <span className="log-entry__time">{formatLogTime(log.asctime)}</span>
                    <span className="log-entry__msg">{log.msg}</span>
                  </li>
                ))}
              </ul>
            ) : (
              <div className="success info">No errors for the last 24 hours</div>
            )}
          </div>
        </>
      )}
    </Tile>
  );
}
