import { NavLink } from "react-router-dom";

interface NavItem {
  to: string;
  label: string;
  end?: boolean;
}

const NAV_ITEMS: NavItem[] = [
  { to: "/", label: "Dashboard", end: true },
  { to: "/sensors/home", label: "Home (chart)" },
  { to: "/sensors/boiler", label: "Boiler (chart)" },
  { to: "/styleguide", label: "Styleguide" },
];

export function Header() {
  return (
    <header className="app-header">
      <div className="app-header__brand">
        <span className="app-header__logo">
          <img src="/static/img/logo.png" alt="O" />
        </span>
        <NavLink to="/">ODIN</NavLink>
      </div>
      <nav className="menu">
        {NAV_ITEMS.map((item) => (
          <NavLink key={item.to} to={item.to} end={item.end}>
            {item.label}
          </NavLink>
        ))}
        <a href="/admin/" target="_blank" rel="noreferrer">
          Admin
        </a>
      </nav>
    </header>
  );
}
