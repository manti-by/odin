import { AliveIndicator, type AliveState } from "@/components/tile/AliveIndicator";
import type { ReactNode } from "react";

interface TileProps {
  title: ReactNode;
  children: ReactNode;
  status?: AliveState;
  iconLink?: ReactNode;
  className?: string;
}

export function Tile({ title, status, iconLink, children, className }: TileProps) {
  return (
    <section className={`tile ${className ? className : ""}`}>
      <h2 className="tile__title">
        {status && <AliveIndicator state={status} />}
        <span className="tile__title-text">{title}</span>
        {iconLink && <span className="tile__icon">{iconLink}</span>}
      </h2>
      <div className="tile__body">{children}</div>
    </section>
  );
}
