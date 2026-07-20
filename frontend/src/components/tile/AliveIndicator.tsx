export type AliveState = "alive" | "dead" | "heating" | "cooling";

interface AliveIndicatorProps {
  state: AliveState;
}

export function AliveIndicator({ state }: AliveIndicatorProps) {
  return <span className={`alive-indicator alive-indicator--${state}`} aria-label={state} />;
}
