import { Icon } from "./Icon";
import { nav } from "./data";
import { Link } from "@tanstack/react-router";

export function Logo() {
  return (
    <div className="logo" aria-label="SIGER">
      <span className="logo-main">SIGER</span>
    </div>
  );
}

export function Header({ compact = false }: { compact?: boolean }) {
  return (
    <header>
      <div className="topbar">
        <div className="container topbar-in">
          <div className="tb-item"><Icon name="pin" size={15} /><div><small>Casa Central</small>Av. 1 y Calle 47</div></div>
          <div className="tb-item"><Icon name="phone" size={15} /><div><small>Teléfonos</small>11 0000-1234</div></div>
          <div className="tb-item"><Icon name="mail" size={15} /><div><small>Correo</small>Siger@transporte.com.ar</div></div>
        </div>
      </div>
      <div className="navbar">
        {/* El logo lleva al inicio desde cualquier página, como en cualquier sitio web */}
        <div className="logo-wrap"><Link to="/" aria-label="Ir al inicio"><Logo /></Link></div>
        <div className="container nav-in">
          {!compact && <><nav className="nav">
            {nav.map((n) => <a key={n.t} href={n.href}>{n.t}</a>)}
            <a href="#contacto" className="nav-cta">Contacto</a>
          </nav>
          <button className="burger" aria-label="Menú"><span /><span /><span /></button></>}
        </div>
      </div>
    </header>
  );
}
