import { ResponsiveGrid } from "@/components/grid/ResponsiveGrid";
import { CurrencyTile } from "@/components/tile/CurrencyTile";
import { Ds18b20SensorsTile } from "@/components/tile/Ds18b20SensorsTile";
import { Esp8266SensorsTile } from "@/components/tile/Esp8266SensorsTile";
import { SystemErrorsTile } from "@/components/tile/SystemErrorsTile";
import { TargetTempModal } from "@/components/tile/TargetTempModal";
import { WeatherTile } from "@/components/tile/WeatherTile";
import { useDashboardData } from "@/hooks/useDashboardData";
import type { DashboardSensor } from "@/lib/api/dashboard";
import { useState } from "react";

export function DashboardPage() {
  const { data, loading, error, reload } = useDashboardData();
  const [selectedSensor, setSelectedSensor] = useState<DashboardSensor | null>(null);

  const handleEditSensor = (sensor: DashboardSensor) => {
    setSelectedSensor(sensor);
  };

  const handleModalClose = () => {
    setSelectedSensor(null);
  };

  const handleModalSuccess = () => {
    void reload();
  };

  if (error && !data) {
    return (
      <section>
        <p className="error" role="alert">
          {error}
        </p>
        <button type="button" onClick={() => void reload()} disabled={loading}>
          {loading ? "Loading..." : "Retry"}
        </button>
      </section>
    );
  }

  return (
    <section>
      {error && (
        <p className="error" role="alert">
          {error}
        </p>
      )}
      <ResponsiveGrid>
        <Esp8266SensorsTile
          sensors={data?.sensors.esp8266 ?? []}
          isAlive={data?.home_sensors_is_alive ?? true}
          onEditSensor={handleEditSensor}
          loading={loading}
        />
        <Ds18b20SensorsTile
          sensors={data?.sensors.ds18b20 ?? []}
          isAlive={data?.boiler_sensors_is_alive ?? true}
          loading={loading}
        />
        <WeatherTile weather={data?.weather ?? null} loading={loading} />
        <CurrencyTile rates={data?.exchange_rates ?? []} trends={data?.exchange_rates_trends ?? {}} loading={loading} />
        <SystemErrorsTile
          traffic={data?.traffic ?? null}
          voltage={data?.voltage ?? null}
          systemdStatus={data?.systemd_status ?? {}}
          errorLogs={data?.error_logs ?? []}
          loading={loading}
        />
      </ResponsiveGrid>
      <TargetTempModal
        open={selectedSensor !== null}
        sensor={selectedSensor}
        onClose={handleModalClose}
        onSuccess={handleModalSuccess}
      />
    </section>
  );
}
