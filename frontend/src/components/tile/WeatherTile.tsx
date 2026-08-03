import { Tile } from "@/components/tile/Tile";
import type { WeatherData } from "@/lib/api/dashboard";

interface WeatherTileProps {
  weather: WeatherData | null;
  loading: boolean;
}

const DIRECTIONS = ["north", "north-east", "east", "south-east", "south", "south-west", "west", "north-west"];

function windDirectionAbbr(degrees: number | null): string {
  if (degrees === null || degrees === undefined) return "";
  const index = Math.floor(((((degrees % 360) + 360) % 360) + 22.5) / 45) % 8;
  return DIRECTIONS[index];
}

export function WeatherTile({ weather, loading }: WeatherTileProps) {
  return (
    <Tile title="Weather">
      {loading ? (
        <p className="tile__loading">Loading...</p>
      ) : !weather ? (
        <p className="tile__empty">No Data</p>
      ) : (
        <>
          <div className="weather-temp attr">
            <span>{weather.temp_display}°C</span>
            <span className="meta info">
              <span>max</span> {weather.temp_max_display}°C
              <br />
              <span>min</span> {weather.temp_min_display}°C
            </span>
          </div>
          <div className="row attr">
            <div className="weather-humidity">
              <span className="weather-humidity__chart">
                <img
                  src={`/api/v1/core/chart/?value=${encodeURIComponent(weather.humidity ?? "")}&metric=humidity`}
                  alt="Humidity chart"
                />
              </span>
              <span className="tile-label">Humidity</span>
            </div>
            <div className="weather-pressure">
              <span className="weather-pressure__chart">
                <img
                  src={`/api/v1/core/chart/?value=${encodeURIComponent(weather.pressure ?? "")}&metric=pressure`}
                  alt="Pressure chart"
                />
              </span>
              <span className="tile-label">Pressure</span>
            </div>
          </div>
          <div className="weather-wind attr row">
            <div className="weather-wind__direction">
              <span style={{ transform: `rotate(${weather.wind.direction ?? 0}deg)` }}>↓</span>
            </div>
            <div>
              <div className="label">
                Wind {windDirectionAbbr(weather.wind.direction)} {weather.wind.speed ?? "-"} m/s
              </div>
              <div className="gusts info">Gusts up to {weather.wind.gusts ?? "-"} m/s</div>
            </div>
          </div>
          {weather.has_attrs && (
            <div className="attributes attr">
              <span className="tile-label">Attributes - </span>
              <span>
                {weather.attributes.fog && "Fog, "}
                {weather.attributes.snow && "Snow, "}
                {weather.attributes.thunderstorm && "Thunderstorm, "}
                {weather.attributes.black_ice && "Black Ice"}
              </span>
            </div>
          )}
        </>
      )}
    </Tile>
  );
}
