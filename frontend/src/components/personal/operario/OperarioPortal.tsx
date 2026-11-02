// Panel del operario: login (HU-01), cerrar sesión (HU-03) y las secciones Pedidos en curso, Registrar pedido,
// Historial, Reportes y Repartidores. La sección, el pedido abierto y los filtros van en la URL
// (/operario?seccion=...&pedido=...): así el botón "atrás" del navegador vuelve a la pantalla anterior.
import { useState, type FormEvent } from "react";
import { useNavigate, useSearch } from "@tanstack/react-router";
import { ArrowRight } from "lucide-react";
import { Button } from "@/components/ui/button";
import { getSesionOperario, loginOperario, tokenOperario, type Estado, type FiltrosHistorial } from "@/lib/api";
import { Marco, SinConexion, useSesion, type SesionActiva } from "../comun";
import { Tablero } from "./Tablero";
import { RegistrarPedido } from "./RegistrarPedido";
import { DetallePedido } from "./DetallePedido";
import { Repartidores } from "./Repartidores";
import { Historial } from "./Historial";
import { Reportes } from "./Reportes";

export const SECCIONES_OPERARIO = ["tablero", "nuevo-pedido", "historial", "reportes", "repartidores"] as const;
export type SeccionOperario = (typeof SECCIONES_OPERARIO)[number];

const NOMBRE_SECCION: Record<SeccionOperario, string> = {
  tablero: "Pedidos en curso",
  "nuevo-pedido": "Registrar pedido",
  historial: "Historial",
  reportes: "Reportes",
  repartidores: "Repartidores",
};

// Lo que puede venir en la URL del panel (lo valida la ruta, en routes/operario.tsx).
export type BusquedaOperario = { seccion?: SeccionOperario; pedido?: number; desde?: string; hasta?: string; estado?: Estado; repartidor?: number };

export function OperarioPortal() {
  const sesion = useSesion(tokenOperario, getSesionOperario);
  const busqueda = useSearch({ from: "/operario" });
  const { seccion = "tablero", pedido } = busqueda;
  const navigate = useNavigate();

  if (sesion.estado === "verificando") {
    return <Marco rol="Operario" titulo="Acceso de personal"><p className="fsub">Verificando sesión…</p></Marco>;
  }
  if (sesion.estado === "sin-conexion") {
    return <Marco rol="Operario" titulo="Acceso de personal"><SinConexion mensaje={sesion.error} onReintentar={sesion.reintentar} /></Marco>;
  }
  if (!sesion.usuario) {
    return <Marco rol="Operario" titulo="Acceso de personal"><LoginOperario error={sesion.error} onIngreso={sesion.iniciar} /></Marco>;
  }

  const activa: SesionActiva = { token: sesion.leerToken() ?? "", manejarError: sesion.manejarError };
  // Se conservan los filtros: al volver del detalle, el historial sigue con la misma búsqueda.
  const abrirPedido = (id: number) => navigate({ to: "/operario", search: { ...busqueda, pedido: id } });
  // Los filtros vacíos no van a la URL.
  const filtrar = (f: { [K in "desde" | "hasta" | "estado" | "repartidor"]?: BusquedaOperario[K] | undefined }) =>
    navigate({ to: "/operario", search: { seccion, ...Object.fromEntries(Object.entries(f).filter(([, v]) => v !== undefined)) } });

  const filtrosHistorial: FiltrosHistorial = {};
  if (busqueda.desde) filtrosHistorial.desde = busqueda.desde;
  if (busqueda.hasta) filtrosHistorial.hasta = busqueda.hasta;
  if (busqueda.estado) filtrosHistorial.estado = busqueda.estado;
  if (busqueda.repartidor) filtrosHistorial.repartidor_id = busqueda.repartidor;

  // HU-03: cierra la sesión y vuelve al ingreso. `replace` reemplaza la página actual en el historial del
  // navegador; y aunque se vuelva atrás, sin token cualquier pantalla del panel muestra el ingreso.
  function salir() {
    sesion.cerrar();
    navigate({ to: "/operario", search: {}, replace: true });
  }

  return (
    <Marco rol="Operario" titulo="Panel de gestión" onSalir={salir}>
      <nav className="staff-actions" style={{ margin: "24px 0" }} aria-label="Secciones del panel">
        {SECCIONES_OPERARIO.map((s) => (
          <Button key={s} type="button" className={s === seccion && pedido === undefined ? "btn btn-primary" : "staff-secondary"}
            variant={s === seccion && pedido === undefined ? "default" : "outline"}
            onClick={() => navigate({ to: "/operario", search: { seccion: s } })}>
            {NOMBRE_SECCION[s]}
          </Button>
        ))}
      </nav>
      {pedido !== undefined ? (
        <DetallePedido key={pedido} id={pedido} sesion={activa} />
      ) : seccion === "tablero" ? (
        <Tablero sesion={activa} onAbrir={abrirPedido} />
      ) : seccion === "nuevo-pedido" ? (
        <RegistrarPedido sesion={activa} onAbrir={abrirPedido} />
      ) : seccion === "historial" ? (
        <Historial sesion={activa} filtros={filtrosHistorial}
          onFiltrar={(f) => filtrar({ desde: f.desde, hasta: f.hasta, estado: f.estado, repartidor: f.repartidor_id })} onAbrir={abrirPedido} />
      ) : seccion === "reportes" ? (
        <Reportes sesion={activa} periodo={{ ...(busqueda.desde ? { desde: busqueda.desde } : {}), ...(busqueda.hasta ? { hasta: busqueda.hasta } : {}) }}
          onPeriodo={(p) => filtrar({ desde: p.desde, hasta: p.hasta })} />
      ) : (
        <Repartidores sesion={activa} />
      )}
    </Marco>
  );
}

// HU-01: el botón queda deshabilitado hasta completar los dos campos (y mientras espera la respuesta).
function LoginOperario({ error, onIngreso }: { error: string; onIngreso: (token: string) => Promise<void> }) {
  const [usuario, setUsuario] = useState("");
  const [contrasena, setContrasena] = useState("");
  const [ingresando, setIngresando] = useState(false);
  const [errorLogin, setErrorLogin] = useState("");
  const puedeIngresar = usuario.trim() !== "" && contrasena !== "" && !ingresando;

  async function ingresar(e: FormEvent) {
    e.preventDefault();
    if (!puedeIngresar) return;
    setIngresando(true);
    try {
      const { token } = await loginOperario(usuario.trim(), contrasena);
      await onIngreso(token);
    } catch (err) {
      // 401 → "Usuario o contraseña incorrectos" (lo manda el backend); sin conexión → el aviso de api.ts
      setErrorLogin((err as Error).message);
      setIngresando(false);
    }
  }

  const mensaje = errorLogin || error;
  return (
    <form className="form staff-login" onSubmit={ingresar} noValidate>
      <h2>Ingresar como operario</h2>
      <div className="fgrid">
        <label className="full">Usuario<input value={usuario} onChange={(e) => setUsuario(e.target.value)} autoComplete="username" maxLength={100} /></label>
        <label className="full">Contraseña<input value={contrasena} onChange={(e) => setContrasena(e.target.value)} type="password" autoComplete="current-password" maxLength={128} /></label>
      </div>
      {mensaje && <p className="staff-error" role="alert">{mensaje}</p>}
      <Button className="btn btn-primary staff-submit" type="submit" disabled={!puedeIngresar}>{ingresando ? "Ingresando…" : "Ingresar"}<ArrowRight /></Button>
    </form>
  );
}
