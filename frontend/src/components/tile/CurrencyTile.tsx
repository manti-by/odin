import { Tile } from "@/components/tile/Tile";
import type { ExchangeRate } from "@/lib/api/dashboard";

interface CurrencyTileProps {
  rates: ExchangeRate[];
  trends: Record<string, number>;
  loading: boolean;
}

function formatDate(dateStr: string): string {
  const [year, month, day] = dateStr.split("-");
  return `${day}.${month}.${year}`;
}

function formatRate(value: string): string {
  const num = Number.parseFloat(value);
  if (Number.isNaN(num)) return "-";
  return num.toFixed(4);
}

export function CurrencyTile({ rates, trends, loading }: CurrencyTileProps) {
  return (
    <Tile title="Exchange Rates">
      {loading ? (
        <p className="tile__loading">Loading...</p>
      ) : rates.length === 0 ? (
        <p className="tile__empty">No Data</p>
      ) : (
        <>
          <div className="currency-date info">{formatDate(rates[0].date)}</div>
          <div className="currency-rates">
            {rates.map((rate) => {
              const trend = trends[rate.currency] ?? 0;
              let trendClass = "trend";
              let trendChar = "-";
              if (trend > 0) {
                trendClass = "trend up";
                trendChar = "\u2191";
              } else if (trend < 0) {
                trendClass = "trend down";
                trendChar = "\u2193";
              }
              return (
                <div key={rate.currency} className="currency-rate">
                  <span className="currency-rate__code">{rate.currency}</span>
                  <span className="currency-rate__value">
                    {formatRate(rate.rate_per_unit)} BYN
                    <span className={trendClass}>{trendChar}</span>
                  </span>
                </div>
              );
            })}
          </div>
        </>
      )}
    </Tile>
  );
}
