// HU-25 Métricas de la operación y HU-26 Rendimiento de repartidores, sobre el mismo período
// (por defecto, el mes en curso). El período elegido va en la URL, como los filtros del historial.
import { useEffect, useState } from "react";
import { ArrowDown, ArrowUp, BarChart3 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { getMetricas, getRendimiento, type Estado, type Metricas, type Periodo, type RendimientoRepartidor } from "@/lib/api";
import { NOMBRE_ESTADO, formatearDia, formatearMinutos, hoyISO } from "@/lib/formato";
import { Aviso, type SesionActiva } from "../comun";

type Props = { sesion: SesionActiva; periodo: Periodo; onPeriodo: (p: Periodo) => void };

export function Reportes({ sesion, periodo, onPeriodo }: Props) {
  const [metricas, setMetricas] = useState<Metricas | null>(null);
  const [rendimiento, setRendimiento] = useState<RendimientoRepartidor[] | null>(null);
  const [error, setError] = useState("");

  const clave = JSON.stringify(periodo);
  useEffect(() => {
    setMetricas(null);
    setRendimiento(null);
    Promise.all([getMetricas(sesion.token, periodo), getRendimiento(sesion.token, periodo)])
      .then(([m, r]) => { setMetricas(m); setRendimiento(r); setError(""); })
      .catch((err) => setError(sesion.manejarError(err)));
  }, [clave]); // eslint-disable-line react-hooks/exhaustive-deps

  return (
    <section aria-labelledby="reportes-titulo">
      <h2 id="reportes-titulo" style={{ fontSize: 20 }}>Reportes</h2>
      {/* key: si cambia el período (p. ej. con el "atrás" del navegador), los campos se reinician */}
      <ElegirPeriodo key={clave} periodo={periodo} onPeriodo={onPeriodo} />
      <Aviso texto={error} error />
      {!metricas || !rendimiento ? (!error && <p className="fsub">Calculando…</p>) : (
        <>
          <p className="fsub" style={{ margin: "16px 0" }}>
            Pedidos registrados {metricas.desde === metricas.hasta ? `el ${formatearDia(metricas.desde)}` : `del ${formatearDia(metricas.desde)} al ${formatearDia(metricas.hasta)}`}
          </p>
          <VistaMetricas m={metricas} />
          <TablaRendimiento filas={rendimiento} />
        </>
      )}
    </section>
  );
}

function ElegirPeriodo({ periodo, onPeriodo }: { periodo: Periodo; onPeriodo: (p: Periodo) => void }) {
  const hoy = hoyISO();
  const [desde, setDesde] = useState(periodo.desde ?? `${hoy.slice(0, 8)}01`); // el día 1 del mes
  const [hasta, setHasta] = useState(periodo.hasta ?? hoy);

  const falta = !desde || !hasta ? "Elegí las dos fechas."
    : desde > hasta ? "La fecha \"desde\" no puede ser posterior a \"hasta\"."
    : hasta > hoy ? "No se puede elegir un día futuro."
    : null;

  return (
    <div className="form shipment-create" style={{ padding: 20 }}>
      <div className="fgrid" style={{ gridTemplateColumns: "repeat(auto-fit, minmax(170px, 1fr))" }}>
        <label>Desde<input type="date" value={desde} max={hasta || hoy} onChange={(e) => setDesde(e.target.value)} /></label>
        <label>Hasta<input type="date" value={hasta} min={desde} max={hoy} onChange={(e) => setHasta(e.target.value)} /></label>
      </div>
      {falta && <p className="hint" style={{ marginBottom: 0 }}>{falta}</p>}
      <Button className="btn btn-primary" style={{ marginTop: 16 }} disabled={!!falta} onClick={() => onPeriodo({ desde, hasta })}><BarChart3 />Ver reportes</Button>
    </div>
  );
}

// HU-25: las 4 métricas. "Tiempo promedio entre pedidos" es ambiguo: se muestran sus dos lecturas.
function VistaMetricas({ m }: { m: Metricas }) {
  const estados = Object.keys(NOMBRE_ESTADO) as Estado[];
  return (
    <div style={{ marginBottom: 32 }}>
      <h3 style={{ fontSize: 18, marginBottom: 12 }}>Métricas de la operación</h3>
      <div className="metricas">
        <Indicador titulo="Pedidos del período" valor={String(m.total_pedidos)} />
        <Indicador titulo="Tiempo promedio de entrega" valor={formatearMinutos(m.minutos_promedio_entrega)} ayuda="De Registrado a Entregado" />
        <Indicador titulo="Entregas fallidas" valor={m.porcentaje_entregas_fallidas === null ? "Sin datos" : `${m.porcentaje_entregas_fallidas.toFixed(1)} %`} ayuda="Sobre las entregas terminadas" />
        <Indicador titulo="Tiempo entre pedidos" valor={formatearMinutos(m.minutos_entre_pedidos)} ayuda="Cada cuánto entra un pedido nuevo" />
        <Indicador titulo="Tiempo entre entregas" valor={formatearMinutos(m.minutos_entre_entregas)} ayuda="De un mismo repartidor, en el día" />
      </div>
      <div className="shipment-table-wrap" style={{ marginTop: 16 }}>
        <table className="shipment-table" style={{ minWidth: 0 }}>
          <caption>Pedidos por estado</caption>
          <tbody>
            {estados.map((e) => <tr key={e}><th scope="row">{NOMBRE_ESTADO[e]}</th><td>{m.pedidos_por_estado[e]}</td></tr>)}
          </tbody>
        </table>
      </div>
    </div>
  );
}

function Indicador({ titulo, valor, ayuda }: { titulo: string; valor: string; ayuda?: string }) {
  return (
    <div className="metrica">
      <small>{titulo}</small>
      <strong>{valor}</strong>
      {ayuda && <span>{ayuda}</span>}
    </div>
  );
}

// HU-26: ordenable tocando el título de cada columna (por defecto, por entregas realizadas).
type Columna = "nombre" | "entregas_realizadas" | "entregas_fallidas" | "minutos_promedio_entrega";
const COLUMNAS: { clave: Columna; titulo: string }[] = [
  { clave: "nombre", titulo: "Repartidor" },
  { clave: "entregas_realizadas", titulo: "Entregas realizadas" },
  { clave: "entregas_fallidas", titulo: "Entregas fallidas" },
  { clave: "minutos_promedio_entrega", titulo: "Tiempo promedio (desde que retira)" },
];

function TablaRendimiento({ filas }: { filas: RendimientoRepartidor[] }) {
  const [orden, setOrden] = useState<{ columna: Columna; descendente: boolean }>({ columna: "entregas_realizadas", descendente: true });

  function ordenarPor(columna: Columna) {
    // Tocar la misma columna invierte el orden; una nueva empieza de mayor a menor (A→Z para el nombre).
    setOrden((o) => o.columna === columna ? { columna, descendente: !o.descendente } : { columna, descendente: columna !== "nombre" });
  }

  const ordenadas = [...filas].sort((a, b) => {
    const x = a[orden.columna];
    const y = b[orden.columna];
    // Los que no tienen tiempo ("Sin datos") van siempre al final.
    if (x === null || y === null) return x === y ? 0 : x === null ? 1 : -1;
    const comparacion = typeof x === "string" ? x.localeCompare(String(y)) : x - Number(y);
    return orden.descendente ? -comparacion : comparacion;
  });

  return (
    <div>
      <h3 style={{ fontSize: 18, marginBottom: 12 }}>Rendimiento de repartidores</h3>
      {filas.length === 0 ? <p className="demo-notice">No hay repartidores registrados.</p> : (
        <div className="shipment-table-wrap">
          <table className="shipment-table" style={{ minWidth: 640 }}>
            <thead>
              <tr>
                {COLUMNAS.map((c) => (
                  <th key={c.clave} scope="col" aria-sort={orden.columna === c.clave ? (orden.descendente ? "descending" : "ascending") : "none"}>
                    <button type="button" onClick={() => ordenarPor(c.clave)} style={{ all: "unset", cursor: "pointer", display: "inline-flex", alignItems: "center", gap: 6 }}>
                      {c.titulo}
                      {orden.columna === c.clave && (orden.descendente ? <ArrowDown size={14} /> : <ArrowUp size={14} />)}
                    </button>
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {ordenadas.map((f) => (
                <tr key={f.id}>
                  <th scope="row">{f.nombre}</th>
                  <td>{f.entregas_realizadas}</td>
                  <td>{f.entregas_fallidas}</td>
                  <td>{formatearMinutos(f.minutos_promedio_entrega)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
