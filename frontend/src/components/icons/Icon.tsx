const ICON_PATHS: Record<string, string> = {
  graph: "/static/img/graph.svg",
  settings: "/static/img/settings.svg",
  schedule: "/static/img/schedule.svg",
  cooling: "/static/img/cooling.svg",
  heating: "/static/img/heating.svg",
};

export type IconName = keyof typeof ICON_PATHS;

interface IconProps {
  name: IconName;
  alt: string;
  width?: number;
  className?: string;
  title?: string;
}

export function Icon({ name, alt, width = 16, className, title }: IconProps) {
  return <img src={ICON_PATHS[name]} alt={alt} width={width} className={className} title={title} />;
}
