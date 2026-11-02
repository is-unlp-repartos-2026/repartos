// App del repartidor: login con código (HU-02), jornada laboral (HU-13 y HU-14) y sus pedidos (HU-16).
// El pedido abierto va en la URL (/repartidor?pedido=...): el "atrás" del celular vuelve a la lista.
import { useState, type FormEvent } from "react";
import { useNavigate, useSearch } from "@tanstack/react-router";
import { ArrowRight, Truck } from "lucide-react";
import { Button } from "@/components/ui/button";
import {
  comenzarJornada, getSesionRepartidor, listarPedidosAsignados, loginRepartidor, terminarJornada, tokenRepartidor,
  type PedidoAsignado, type Repartidor,
} from "@/lib/api";
import { NOMBRE_ESTADO, formatearFecha } from "@/lib/formato";
import { Aviso, Marco, SinConexion, useCadaTanto, useSesion, type SesionActiva } from "../comun";
import { DetallePedidoAsignado } from "./DetallePedidoAsignado";

export function RepartidorPortal() {
  const sesion = useSesion(tokenRepartidor, getSesionRepartidor);
  const { pedido } = useSearch({ from: "/repartidor" });
  const navigate = useNavigate();
  // Resultado de la última acción (p. ej. "Entrega confirmada"): se muestra al volver a la lista.
  const [aviso, setAviso] = useState("");

  if (sesion.estado === "verificando") {
    return <Marco rol="Repartidor" titulo="Acceso de repartidor"><p className="fsub">Verificando sesión…</p></Marco>;
  }
  if (sesion.estado === "sin-conexion") {
    return <Marco rol="Repartidor" titulo="Acceso de repartidor"><SinConexion mensaje={sesion.error} onReintentar={sesion.reintentar} /></Marco>;
  }
  if (!sesion.usuario) {
    return <Marco rol="Repartidor" titulo="Acceso de repartidor"><LoginRepartidor error={sesion.error} onIngreso={sesion.iniciar} /></Marco>;
  }

  const activa: SesionActiva = { token: sesion.leerToken() ?? "", manejarError: sesion.manejarError };
  const repartidor = sesion.usuario;

  return (
    <Marco rol="Repartidor" titulo={`Hola, ${repartidor.nombre}`} onSalir={() => sesion.cerrar()}>
      {pedido !== undefined ? (
        <DetallePedidoAsignado key={pedido} id={pedido} sesion={activa}
          onTerminado={(texto) => { setAviso(texto); navigate({ to: "/repartidor", search: {} }); }} />
      ) : (
        <>
          <Jornada repartidor={repartidor} sesion={activa} onCambio={(activo) => sesion.setUsuario({ ...repartidor, activo })} onAviso={setAviso} />
          <Aviso texto={aviso} />
          <MisPedidos sesion={activa} onAbrir={(id) => { setAviso(""); navigate({ to: "/repartidor", search: { pedido: id } }); }} />
        </>
      )}
    </Marco>
  );
}

// HU-02: solo letras y números, en mayúscula; el botón se habilita con los 4 caracteres.
const LARGO_CODIGO_ACCESO = 4;
const limpiarCodigo = (valor: string) => valor.toUpperCase().replace(/[^A-Z0-9]/g, "").slice(0, LARGO_CODIGO_ACCESO);

function LoginRepartidor({ error, onIngreso }: { error: string; onIngreso: (token: string) => Promise<void> }) {
  const [codigo, setCodigo] = useState("");
  const [ingresando, setIngresando] = useState(false);
  const [errorLogin, setErrorLogin] = useState("");
  const puedeIngresar = codigo.length === LARGO_CODIGO_ACCESO && !ingresando;

  async function ingresar(e: FormEvent) {
    e.preventDefault();
    if (!puedeIngresar) return;
    setIngresando(true);
    try {
      const { token } = await loginRepartidor(codigo);
      await onIngreso(token); // la sesión queda guardada en el celular
    } catch (err) {
      setErrorLogin((err as Error).message); // código incorrecto (401) o repartidor deshabilitado (403)
      setIngresando(false);
    }
  }

  const mensaje = errorLogin || error;
  return (
    <form className="form staff-login" onSubmit={ingresar} noValidate>
      <h2>Ingresá tu código</h2>
      <div className="fgrid">
        <label className="full">Código de acceso ({LARGO_CODIGO_ACCESO} caracteres)
          <input value={codigo} onChange={(e) => setCodigo(limpiarCodigo(e.target.value))} autoComplete="off" style={{ letterSpacing: "0.3em" }} />
        </label>
      </div>
      {mensaje && <p className="staff-error" role="alert">{mensaje}</p>}
      <Button className="btn btn-primary staff-submit" type="submit" disabled={!puedeIngresar}>{ingresando ? "Verificando…" : "Ingresar"}<ArrowRight /></Button>
    </form>
  );
}

// HU-13 / HU-14: un solo botón que cambia según si está activo o no.
// Terminar con pedidos en camino no se permite: lo avisa el backend (es un criterio de aceptación).
function Jornada({ repartidor, sesion, onCambio, onAviso }: {
  repartidor: Repartidor; sesion: SesionActiva; onCambio: (activo: boolean) => void; onAviso: (texto: string) => void;
}) {
  const [enviando, setEnviando] = useState(false);
  const [error, setError] = useState("");

  async function cambiar() {
    setEnviando(true);
    setError("");
    onAviso("");
    try {
      if (repartidor.activo) {
        const r = await terminarJornada(sesion.token);
        const liberados = r.pedidos_reasignados + r.pedidos_sin_repartidor;
        onAviso(liberados > 0 ? `Terminaste tu jornada. Tus pedidos sin retirar (${liberados}) pasaron a otros repartidores.` : "Terminaste tu jornada.");
        onCambio(false);
      } else {
        const r = await comenzarJornada(sesion.token);
        onAviso(r.pedidos_asignados > 0 ? `Comenzaste tu jornada. Se te asignaron ${r.pedidos_asignados} pedidos pendientes.` : "Comenzaste tu jornada.");
        onCambio(true);
      }
    } catch (err) {
      setError(sesion.manejarError(err));
    } finally {
      setEnviando(false);
    }
  }

  return (
    <>
      <div style={{ marginTop: 20, padding: 16, border: "1px solid var(--border)", borderRadius: 8, display: "flex", justifyContent: "space-between", alignItems: "center", gap: 12, flexWrap: "wrap" }}>
        <span>Estado: <strong>{repartidor.activo ? "Activo" : "Inactivo"}</strong></span>
        <Button className={repartidor.activo ? "staff-secondary" : "btn btn-primary"} variant={repartidor.activo ? "outline" : "default"} disabled={enviando} onClick={cambiar}>
          {enviando ? "Un momento…" : repartidor.activo ? "Terminar jornada laboral" : "Comenzar jornada laboral"}
        </Button>
      </div>
      <Aviso texto={error} error />
    </>
  );
}

// HU-16: origen, destino y estado; nunca el contenido. Se actualiza solo para que vea los pedidos nuevos.
function MisPedidos({ sesion, onAbrir }: { sesion: SesionActiva; onAbrir: (id: number) => void }) {
  const [pedidos, setPedidos] = useState<PedidoAsignado[] | null>(null);
  const [error, setError] = useState("");

  useCadaTanto(() => {
    listarPedidosAsignados(sesion.token)
      .then((p) => { setPedidos(p); setError(""); })
      .catch((err) => setError(sesion.manejarError(err)));
  }, 10000);

  return (
    <section style={{ marginTop: 24 }}>
      <h2 style={{ fontSize: 20 }}>Mis pedidos</h2>
      <Aviso texto={error} error />
      {pedidos === null ? (!error && <p className="fsub">Cargando pedidos…</p>)
        : pedidos.length === 0 ? <p className="demo-notice">No tenés pedidos asignados.</p>
        : (
          <div style={{ display: "grid", gap: 16, marginTop: 16 }}>
            {pedidos.map((p) => (
              <button type="button" key={p.id} className="tablero-item" onClick={() => onAbrir(p.id)}>
                <span className="shipment-card-head"><strong><Truck size={16} style={{ display: "inline", marginRight: 6 }} />{p.destino}</strong><span className="staff-status">{NOMBRE_ESTADO[p.estado]}</span></span>
                <span>Retirar en: {p.origen}</span>
                <small>Asignado el {formatearFecha(p.asignado_el)}</small>
              </button>
            ))}
          </div>
        )}
    </section>
  );
}
