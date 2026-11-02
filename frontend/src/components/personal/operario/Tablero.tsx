// HU-22: los pedidos en curso agrupados por estado. Se actualiza solo (le pide el tablero al backend cada 5 s),
// así cuando un repartidor retira un pedido, el operario lo ve pasar a "En camino" sin recargar.
// Tocar un pedido abre su detalle (HU-23).
import { useState } from "react";
import { getTablero, type PedidoEnTablero, type Tablero as DatosTablero } from "@/lib/api";
import { formatearFecha } from "@/lib/formato";
import { Aviso, useCadaTanto, type SesionActiva } from "../comun";

const SEGUNDOS_ENTRE_ACTUALIZACIONES = 5;

const GRUPOS: { clave: keyof DatosTablero; titulo: string; vacio: string }[] = [
  { clave: "registrado", titulo: "Registrado (sin repartidor)", vacio: "No hay pedidos sin repartidor." },
  { clave: "repartidor_asignado", titulo: "Repartidor asignado", vacio: "No hay pedidos esperando ser retirados." },
  { clave: "en_camino", titulo: "En camino", vacio: "No hay pedidos en camino." },
];

export function Tablero({ sesion, onAbrir }: { sesion: SesionActiva; onAbrir: (id: number) => void }) {
  const [tablero, setTablero] = useState<DatosTablero | null>(null);
  const [error, setError] = useState("");
  const [actualizado, setActualizado] = useState<Date | null>(null);

  useCadaTanto(() => {
    getTablero(sesion.token)
      .then((t) => { setTablero(t); setError(""); setActualizado(new Date()); })
      .catch((err) => setError(sesion.manejarError(err)));
  }, SEGUNDOS_ENTRE_ACTUALIZACIONES * 1000);

  return (
    <section aria-labelledby="tablero-titulo">
      <div className="staff-toolbar">
        <h2 id="tablero-titulo" style={{ margin: 0, fontSize: 20 }}>Pedidos en curso</h2>
        {actualizado && <small style={{ color: "var(--m-muted)" }}>Se actualiza solo · última vez {actualizado.toLocaleTimeString("es-AR")}</small>}
      </div>
      <Aviso texto={error} error />
      {!tablero ? (
        !error && <p className="fsub">Cargando pedidos…</p>
      ) : (
        <div className="tablero">
          {GRUPOS.map((g) => (
            <div key={g.clave} className="tablero-col">
              <h3>{g.titulo} <span className="tablero-cantidad">{tablero[g.clave].length}</span></h3>
              {tablero[g.clave].length === 0 && <p className="fsub">{g.vacio}</p>}
              {tablero[g.clave].map((p) => (
                <TarjetaPedido key={p.id} pedido={p} destacado={g.clave === "registrado"} onAbrir={onAbrir} />
              ))}
            </div>
          ))}
        </div>
      )}
    </section>
  );
}

// Los "Registrado" se destacan: son los que necesitan atención porque no tienen repartidor.
function TarjetaPedido({ pedido, destacado, onAbrir }: { pedido: PedidoEnTablero; destacado: boolean; onAbrir: (id: number) => void }) {
  return (
    <button type="button" className={destacado ? "tablero-item destacado" : "tablero-item"} onClick={() => onAbrir(pedido.id)}>
      <strong className="tablero-codigo">{pedido.codigo_seguimiento}</strong>
      <span>{pedido.origen} → {pedido.destino}</span>
      <small>{pedido.repartidor ? pedido.repartidor.nombre : "Sin repartidor"} · desde {formatearFecha(pedido.desde)}</small>
    </button>
  );
}
