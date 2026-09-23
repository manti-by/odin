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
import { useErrorLogs } from "@/hooks/useErrorLogs";
import { useExchangeRates } from "@/hooks/useExchangeRates";
import { useDs18B20Dashboard, useEsp8266Dashboard } from "@/hooks/useSensorsDashboard";
import { useSystemdStatus } from "@/hooks/useSystemdStatus";
import { useTraffic } from "@/hooks/useTraffic";
import { useVoltage } from "@/hooks/useVoltage";
import { useWeather } from "@/hooks/useWeather";
import type { RelayType } from "@/lib/api/relays";
import type { DashboardRelay, DashboardSensor } from "@/lib/api/sensors-dashboard";
import { useState } from "react";

function toRelayType(value: string | undefined): RelayType {
  return value === "PUMP" || value === "SERVO" || value === "VALVE" ? value : "VALVE";
}

export function DashboardPage() {
  const esp8266 = useEsp8266Dashboard();
  const ds18b20 = useDs18B20Dashboard();
  const weather = useWeather();
  const boiler = useBoilerStatus();
  const exchangeRates = useExchangeRates();
  const voltage = useVoltage();
  const traffic = useTraffic();
  const errorLogs = useErrorLogs();
  const systemd = useSystemdStatus();
  const [selectedSensor, setSelectedSensor] = useState<DashboardSensor | null>(null);
  const [selectedRelay, setSelectedRelay] = useState<DashboardRelay | null>(null);

  const handleEditSensor = (sensor: DashboardSensor) => {
    setSelectedSensor(sensor);
  };

  const handleModalClose = () => {
    setSelectedSensor(null);
  };

  const handleModalSuccess = () => {
    if (selectedSensor?.type === "ESP8266") {
      esp8266.reload();
    } else {
      ds18b20.reload();
    }
  };

  const handleEditRelaySchedule = (relay: DashboardRelay) => {
    setSelectedRelay(relay);
  };

  const handleRelayModalClose = () => {
    setSelectedRelay(null);
  };

  const handleRelayModalSuccess = () => {
    esp8266.reload();
  };

  return (
    <section>
      <ResponsiveGrid>
        <Esp8266SensorsTile
          sensors={esp8266.data?.sensors ?? []}
          isAlive={esp8266.data?.is_alive ?? true}
          onEditSensor={handleEditSensor}
          onEditRelaySchedule={handleEditRelaySchedule}
          loading={esp8266.loading}
          error={esp8266.error}
        />
        <Ds18b20SensorsTile
          sensors={ds18b20.data?.sensors ?? []}
          isAlive={ds18b20.data?.is_alive ?? true}
          loading={ds18b20.loading}
          error={ds18b20.error}
        />
        <WeatherTile weather={weather.data} loading={weather.loading} error={weather.error} />
        <BoilerTile status={boiler.data} loading={boiler.loading} error={boiler.error} />
        <CurrencyTile
          rates={exchangeRates.data?.rates ?? []}
          trends={exchangeRates.data?.trends ?? {}}
          loading={exchangeRates.loading}
          error={exchangeRates.error}
        />
        <SystemErrorsTile
          traffic={traffic.data}
          voltage={voltage.data}
          systemdStatus={systemd.data ?? {}}
          errorLogs={errorLogs.data ?? []}
          loading={voltage.loading || traffic.loading || errorLogs.loading || systemd.loading}
          error={voltage.error ?? traffic.error ?? errorLogs.error ?? systemd.error}
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
