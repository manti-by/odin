export type AliveState = "alive" | "dead" | "unknown" | "ignored";

interface AliveIndicatorProps {
  state: AliveState;
  title?: string;
}

export function AliveIndicator({ state, title }: AliveIndicatorProps) {
  return <span className={`alive-indicator alive-indicator--${state}`} aria-label={state} title={title} />;
}
