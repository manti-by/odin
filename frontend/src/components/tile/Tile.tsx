import { AliveIndicator, type AliveState } from "@/components/tile/AliveIndicator";
import type { ReactNode } from "react";

interface TileProps {
  title: string;
  status?: AliveState;
  iconLink?: ReactNode;
  children: ReactNode;
}

export function Tile({ title, status, iconLink, children }: TileProps) {
  return (
    <section className="tile">
      <h2 className="tile__title">
        {status && <AliveIndicator state={status} />}
        <span className="tile__title-text">{title}</span>
        {iconLink && <span className="tile__icon">{iconLink}</span>}
      </h2>
      <div className="tile__body">{children}</div>
    </section>
  );
}
