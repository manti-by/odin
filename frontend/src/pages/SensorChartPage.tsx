import { useParams } from "react-router-dom";

type SensorLocation = "home" | "boiler";

const TITLES: Record<SensorLocation, string> = {
  home: "Home temperature",
  boiler: "Boiler temperature",
};

function isSensorLocation(value: string | undefined): value is SensorLocation {
  return value === "home" || value === "boiler";
}

export function SensorChartPage() {
  const { location } = useParams();
  const sensorLocation = isSensorLocation(location) ? location : "home";
  const title = TITLES[sensorLocation];

  return (
    <section>
      <h2>{title}</h2>
      <p className="placeholder">
        Temperature chart for <code>/sensors/{sensorLocation}</code> will be implemented in a follow-up ticket.
      </p>
    </section>
  );
}
