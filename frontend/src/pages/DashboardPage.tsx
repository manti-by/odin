import { ApiError } from "@/lib/api/client";
import { type Sensor, sensorsApi } from "@/lib/api/sensors";
import { useCallback, useEffect, useState } from "react";

export function DashboardPage() {
  const [sensors, setSensors] = useState<Sensor[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  const loadSensors = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const response = await sensorsApi.list();
      setSensors(response.results);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to load sensors");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void loadSensors();
  }, [loadSensors]);

  return (
    <section>
      <h2>Dashboard</h2>
      <p className="placeholder">Dashboard tiles will be implemented in a follow-up ticket.</p>

      <div className="api-smoke">
        <h3>API smoke test — GET /api/v1/sensors/</h3>
        {loading && <p>Loading…</p>}
        {error && (
          <p className="error" role="alert">
            {error}
          </p>
        )}
        {!loading && !error && (
          <>
            <p>
              Loaded <strong>{sensors.length}</strong> active sensor(s).
            </p>
            {sensors.length > 0 && (
              <ul>
                {sensors.map((s) => (
                  <li key={s.sensor_id}>
                    {s.name} ({s.type}) — {s.temp}°C
                  </li>
                ))}
              </ul>
            )}
          </>
        )}
        <button type="button" onClick={() => void loadSensors()} disabled={loading}>
          Reload
        </button>
      </div>
    </section>
  );
}
