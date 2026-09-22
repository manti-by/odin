import { ResponsiveGrid } from "@/components/grid/ResponsiveGrid";
import { BoilerTile } from "@/components/tile/BoilerTile";
import { CurrencyTile } from "@/components/tile/CurrencyTile";
import { Ds18b20SensorsTile } from "@/components/tile/Ds18b20SensorsTile";
import { Esp8266SensorsTile } from "@/components/tile/Esp8266SensorsTile";
import { RelayScheduleModal } from "@/components/tile/RelayScheduleModal";
import { SystemErrorsTile } from "@/components/tile/SystemErrorsTile";
import { TargetTempModal } from "@/components/tile/TargetTempModal";
import { WeatherTile } from "@/components/tile/WeatherTile";
import { useBoilerStatus } from "@/hooks/useBoilerStatus";
import { useDashboardData } from "@/hooks/useDashboardData";
import type { DashboardRelay, DashboardSensor } from "@/lib/api/dashboard";
import type { RelayType } from "@/lib/api/relays";
import { useState } from "react";

function toRelayType(value: string | undefined): RelayType {
  return value === "PUMP" || value === "SERVO" || value === "VALVE" ? value : "VALVE";
}

export function DashboardPage() {
  const { data, loading, error, reload } = useDashboardData();
  const { data: boiler, loading: boilerLoading, error: boilerError } = useBoilerStatus();
  const [selectedSensor, setSelectedSensor] = useState<DashboardSensor | null>(null);
  const [selectedRelay, setSelectedRelay] = useState<DashboardRelay | null>(null);

  const handleEditSensor = (sensor: DashboardSensor) => {
    setSelectedSensor(sensor);
  };

  const handleModalClose = () => {
    setSelectedSensor(null);
  };

  const handleModalSuccess = () => {
    void reload();
  };

  const handleEditRelaySchedule = (relay: DashboardRelay) => {
    setSelectedRelay(relay);
  };

  const handleRelayModalClose = () => {
    setSelectedRelay(null);
  };

  const handleRelayModalSuccess = () => {
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
          onEditRelaySchedule={handleEditRelaySchedule}
          loading={loading}
        />
        <Ds18b20SensorsTile
          sensors={data?.sensors.ds18b20 ?? []}
          isAlive={data?.boiler_sensors_is_alive ?? true}
          loading={loading}
        />
        <WeatherTile weather={data?.weather ?? null} loading={loading} />
        <BoilerTile status={boiler} loading={boilerLoading} error={boilerError} />
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
      <RelayScheduleModal
        open={selectedRelay !== null}
        relayId={selectedRelay?.relay_id ?? null}
        relayName={selectedRelay?.name ?? ""}
        relayType={toRelayType(selectedRelay?.type)}
        onClose={handleRelayModalClose}
        onSuccess={handleRelayModalSuccess}
      />
    </section>
  );
}
