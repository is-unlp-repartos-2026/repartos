// HU-24: el historial de pedidos. Por defecto, los de hoy; filtros por fechas, estado y repartidor.
// Los filtros aplicados van en la URL: al volver del detalle de un pedido, la búsqueda sigue ahí.
// Las fechas no permiten un "desde" posterior al "hasta" ni días futuros (el botón no se habilita).
import { useEffect, useState } from "react";
import { Search } from "lucide-react";
import { Button } from "@/components/ui/button";
import { historialPedidos, listarRepartidores, type Estado, type FiltrosHistorial, type PedidoEnHistorial, type Repartidor } from "@/lib/api";
import { NOMBRE_ESTADO, formatearDia, formatearFecha, hoyISO } from "@/lib/formato";
import { Aviso, type SesionActiva } from "../comun";

const ESTADOS = Object.keys(NOMBRE_ESTADO) as Estado[];

type Props = { sesion: SesionActiva; filtros: FiltrosHistorial; onFiltrar: (f: FiltrosHistorial) => void; onAbrir: (id: number) => void };

export function Historial({ sesion, filtros, onFiltrar, onAbrir }: Props) {
  const [pedidos, setPedidos] = useState<PedidoEnHistorial[] | null>(null);
  const [repartidores, setRepartidores] = useState<Repartidor[]>([]);
  const [error, setError] = useState("");

  // Cada vez que cambian los filtros de la URL, se vuelve a pedir el historial.
  const clave = JSON.stringify(filtros);
  useEffect(() => {
    setPedidos(null);
    historialPedidos(sesion.token, filtros)
      .then((p) => { setPedidos(p); setError(""); })
      .catch((err) => setError(sesion.manejarError(err)));
  }, [clave]); // eslint-disable-line react-hooks/exhaustive-deps

  // Para el filtro por repartidor (todos, también los deshabilitados: su historial se conserva).
  useEffect(() => {
    listarRepartidores(sesion.token).then(setRepartidores).catch(() => setRepartidores([]));
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  const desde = filtros.desde ?? hoyISO();
  const hasta = filtros.hasta ?? hoyISO();

  return (
    <section aria-labelledby="historial-titulo">
      <h2 id="historial-titulo" style={{ fontSize: 20 }}>Historial de pedidos</h2>
      <Filtros key={clave} filtros={filtros} repartidores={repartidores} onFiltrar={onFiltrar} />
      <p className="fsub" style={{ margin: "16px 0" }}>
        {desde === hasta ? `Pedidos registrados el ${formatearDia(desde)}` : `Pedidos registrados del ${formatearDia(desde)} al ${formatearDia(hasta)}`}
        {pedidos && ` · ${pedidos.length} ${pedidos.length === 1 ? "pedido" : "pedidos"}`}
      </p>
      <Aviso texto={error} error />
      {pedidos === null ? (!error && <p className="fsub">Buscando…</p>)
        : pedidos.length === 0 ? <p className="demo-notice">No hay pedidos para los filtros elegidos.</p>
        : (
          <div className="shipment-table-wrap">
            <table className="shipment-table" style={{ minWidth: 800 }}>
              <thead>
                <tr><th scope="col">Código</th><th scope="col">Registrado</th><th scope="col">Origen → Destino</th><th scope="col">Estado</th><th scope="col">Repartidor</th><th scope="col"><span className="sr-only">Acciones</span></th></tr>
              </thead>
              <tbody>
                {pedidos.map((p) => (
                  <tr key={p.id}>
                    <th scope="row" style={{ letterSpacing: "0.1em" }}>{p.codigo_seguimiento}</th>
                    <td>{formatearFecha(p.registrado_el)}</td>
                    <td>{p.origen} → {p.destino}</td>
                    <td>{NOMBRE_ESTADO[p.estado]}</td>
                    <td>{p.repartidor?.nombre ?? "Sin repartidor"}</td>
                    <td><Button size="sm" variant="outline" onClick={() => onAbrir(p.id)}>Ver detalle</Button></td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
    </section>
  );
}

function Filtros({ filtros, repartidores, onFiltrar }: { filtros: FiltrosHistorial; repartidores: Repartidor[]; onFiltrar: (f: FiltrosHistorial) => void }) {
  const hoy = hoyISO();
  const [desde, setDesde] = useState(filtros.desde ?? hoy);
  const [hasta, setHasta] = useState(filtros.hasta ?? hoy);
  const [estado, setEstado] = useState<Estado | "">(filtros.estado ?? "");
  const [repartidor, setRepartidor] = useState(filtros.repartidor_id ? String(filtros.repartidor_id) : "");

  // Un <input type="date"> deja escribir cualquier fecha con el teclado: se valida igual.
  const falta = !desde || !hasta ? "Elegí las dos fechas."
    : desde > hasta ? "La fecha \"desde\" no puede ser posterior a \"hasta\"."
    : hasta > hoy ? "No se puede elegir un día futuro."
    : null;

  function buscar() {
    if (falta) return;
    const f: FiltrosHistorial = { desde, hasta };
    if (estado) f.estado = estado;
    if (repartidor) f.repartidor_id = Number(repartidor);
    onFiltrar(f);
  }

  return (
    <div className="form shipment-create" style={{ padding: 20 }}>
      <div className="fgrid" style={{ gridTemplateColumns: "repeat(auto-fit, minmax(170px, 1fr))" }}>
        <label>Desde<input type="date" value={desde} max={hasta || hoy} onChange={(e) => setDesde(e.target.value)} /></label>
        <label>Hasta<input type="date" value={hasta} min={desde} max={hoy} onChange={(e) => setHasta(e.target.value)} /></label>
        <label>Estado
          <select value={estado} onChange={(e) => setEstado(e.target.value as Estado | "")}>
            <option value="">Todos</option>
            {ESTADOS.map((e) => <option key={e} value={e}>{NOMBRE_ESTADO[e]}</option>)}
          </select>
        </label>
        <label>Repartidor
          <select value={repartidor} onChange={(e) => setRepartidor(e.target.value)}>
            <option value="">Todos</option>
            {repartidores.map((r) => <option key={r.id} value={r.id}>{r.nombre}{r.habilitado ? "" : " (deshabilitado)"}</option>)}
          </select>
        </label>
      </div>
      {falta && <p className="hint" style={{ marginBottom: 0 }}>{falta}</p>}
      <Button className="btn btn-primary" style={{ marginTop: 16 }} disabled={!!falta} onClick={buscar}><Search />Buscar</Button>
    </div>
  );
}
