import { AliveIndicator, type AliveState } from "@/components/tile/AliveIndicator";

interface HomeIndicatorLinkProps {
  href: string;
  state: AliveState;
}

export function HomeIndicatorLink({ href, state }: HomeIndicatorLinkProps) {
  return (
    <a href={href}>
      <AliveIndicator state={state} />
    </a>
  );
}
