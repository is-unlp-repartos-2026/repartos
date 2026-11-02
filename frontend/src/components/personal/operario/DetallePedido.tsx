// HU-23: el detalle de un pedido (se abre desde el tablero). Entregado → además foto y DNI;
// entrega fallida → además el motivo. Se actualiza solo, como el tablero.
// Acá están también las acciones, y cada botón aparece SOLO en los estados en que se permite:
//   HU-05 Modificar → "Registrado" o "Repartidor asignado"
//   HU-06 Cancelar  → "Registrado" o "Repartidor asignado"
//   HU-08 Reasignar → "Repartidor asignado" (el motivo es obligatorio)
import { useEffect, useState } from "react";
import { Ban, Pencil, Shuffle } from "lucide-react";
import { Button } from "@/components/ui/button";
import {
  cancelarPedido, getDetallePedido, getFotoPedido, modificarPedido, reasignarPedido, type DetallePedidoOperario,
} from "@/lib/api";
import { NOMBRE_ESTADO, formatearFecha, formatearMedidas } from "@/lib/formato";
import { Aviso, Ventana, useCadaTanto, type SesionActiva } from "../comun";
import { CamposPedido, borradorDe, datosDe, queFaltaPedido } from "./CamposPedido";

const LARGO_MAX_MOTIVO = 150;

export function DetallePedido({ id, sesion }: { id: number; sesion: SesionActiva }) {
  const [pedido, setPedido] = useState<DetallePedidoOperario | null>(null);
  const [error, setError] = useState("");
  const [aviso, setAviso] = useState("");
  const [ventana, setVentana] = useState<"modificar" | "cancelar" | "reasignar" | null>(null);

  function cargar() {
    getDetallePedido(sesion.token, id)
      .then((p) => { setPedido(p); setError(""); })
      .catch((err) => setError(sesion.manejarError(err)));
  }
  useCadaTanto(cargar, 5000);

  if (!pedido) return error ? <Aviso texto={error} error /> : <p className="fsub">Cargando pedido…</p>;

  // Modificar y cancelar: solo mientras el pedido no fue retirado.
  const puedeCancelar = pedido.estado === "registrado" || pedido.estado === "repartidor_asignado";
  const puedeModificar = puedeCancelar;
  const puedeReasignar = pedido.estado === "repartidor_asignado";

  return (
    <article className="shipment-card" style={{ maxWidth: "none" }}>
      <div className="shipment-card-head">
        <h2>Pedido {pedido.codigo_seguimiento}</h2>
        <span className="staff-status" role="status">{NOMBRE_ESTADO[pedido.estado]}</span>
      </div>
      <Aviso texto={aviso} />
      <Aviso texto={error} error />

      <dl className="shipment-details">
        <div><dt>Origen</dt><dd>{pedido.origen}</dd></div>
        <div><dt>Destino</dt><dd>{pedido.destino}</dd></div>
        <div><dt>Recibe</dt><dd>{pedido.receptor_nombre}</dd></div>
        <div><dt>DNI de quien recibe</dt><dd>{pedido.receptor_dni}</dd></div>
        <div><dt>Peso</dt><dd>{pedido.peso_kg} kg</dd></div>
        <div><dt>Medidas (alto × ancho × largo)</dt><dd>{formatearMedidas(pedido.alto_cm, pedido.ancho_cm, pedido.largo_cm)}</dd></div>
        <div><dt>Repartidor</dt><dd>{pedido.repartidor?.nombre ?? "Sin repartidor"}</dd></div>
        {pedido.motivo_fallo && <div><dt>Motivo de la entrega fallida</dt><dd>{pedido.motivo_fallo}</dd></div>}
      </dl>

      {pedido.estado === "entregado" && <FotoEntrega id={pedido.id} sesion={sesion} />}

      {(puedeModificar || puedeCancelar || puedeReasignar) && (
        <div className="staff-actions" style={{ marginBottom: 30 }}>
          {puedeModificar && <Button variant="outline" className="staff-secondary" onClick={() => setVentana("modificar")}><Pencil />Modificar</Button>}
          {puedeReasignar && <Button variant="outline" className="staff-secondary" onClick={() => setVentana("reasignar")}><Shuffle />Reasignar</Button>}
          {puedeCancelar && <Button variant="outline" className="staff-secondary" onClick={() => setVentana("cancelar")}><Ban />Cancelar pedido</Button>}
        </div>
      )}

      <h3 style={{ fontSize: 18 }}>Historial</h3>
      <ol style={{ paddingLeft: 18, marginTop: 12, lineHeight: 1.8 }}>
        {pedido.historial.map((h, i) => (
          <li key={i}>
            {/* Una corrección de datos (HU-05) no es un cambio de estado */}
            <strong>{h.modificacion ? "Modificación" : NOMBRE_ESTADO[h.estado]}</strong> — {formatearFecha(h.fecha_hora)}
            {h.repartidor && <> · {h.repartidor.nombre}</>}
            {h.detalle && <> · <em>{h.detalle}</em></>}
          </li>
        ))}
      </ol>

      {ventana === "modificar" && <ModificarPedido pedido={pedido} sesion={sesion}
        onCerrar={() => setVentana(null)} onListo={(texto) => { setVentana(null); setAviso(texto); cargar(); }} />}
      <ConfirmarCancelacion abierta={ventana === "cancelar"} pedido={pedido} sesion={sesion}
        onCerrar={() => setVentana(null)} onListo={(texto) => { setVentana(null); setAviso(texto); cargar(); }} />
      <PedirReasignacion abierta={ventana === "reasignar"} pedido={pedido} sesion={sesion}
        onCerrar={() => setVentana(null)} onListo={(texto) => { setVentana(null); setAviso(texto); cargar(); }} />
    </article>
  );
}

type PropsVentana = { abierta: boolean; pedido: DetallePedidoOperario; sesion: SesionActiva; onCerrar: () => void; onListo: (aviso: string) => void };

// HU-06: "Cancelado" es final, por eso se pide confirmación.
function ConfirmarCancelacion({ abierta, pedido, sesion, onCerrar, onListo }: PropsVentana) {
  const [enviando, setEnviando] = useState(false);
  const [error, setError] = useState("");

  async function cancelar() {
    setEnviando(true);
    try {
      await cancelarPedido(sesion.token, pedido.id);
      onListo("El pedido quedó cancelado.");
    } catch (err) {
      setError(sesion.manejarError(err));
    } finally {
      setEnviando(false);
    }
  }

  return (
    <Ventana abierta={abierta} titulo={`¿Cancelar el pedido ${pedido.codigo_seguimiento}?`} descripcion="Un pedido cancelado no se puede volver a activar." onCerrar={onCerrar}>
      <Aviso texto={error} error />
      <div className="staff-actions">
        <Button className="btn btn-primary" disabled={enviando} onClick={cancelar}>{enviando ? "Cancelando…" : "Sí, cancelar pedido"}</Button>
        <Button variant="outline" className="staff-secondary" onClick={onCerrar}>No, volver</Button>
      </div>
    </Ventana>
  );
}

// HU-08: se busca otro repartidor apto (excluyendo al actual); si no hay, vuelve a "Registrado" con aviso.
function PedirReasignacion({ abierta, pedido, sesion, onCerrar, onListo }: PropsVentana) {
  const [motivo, setMotivo] = useState("");
  const [enviando, setEnviando] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => { if (abierta) { setMotivo(""); setError(""); } }, [abierta]);

  async function reasignar() {
    setEnviando(true);
    try {
      const r = await reasignarPedido(sesion.token, pedido.id, motivo.trim());
      onListo(r.repartidor ? `El pedido se reasignó a ${r.repartidor.nombre}.` : r.aviso ?? "No había otro repartidor apto: el pedido quedó Registrado.");
    } catch (err) {
      setError(sesion.manejarError(err));
    } finally {
      setEnviando(false);
    }
  }

  return (
    <Ventana abierta={abierta} titulo={`Reasignar el pedido ${pedido.codigo_seguimiento}`}
      descripcion={`Se le quita a ${pedido.repartidor?.nombre ?? "su repartidor"} y se asigna a otro repartidor apto.`} onCerrar={onCerrar}>
      <label className="fgrid" style={{ display: "block" }}>Motivo
        <textarea value={motivo} maxLength={LARGO_MAX_MOTIVO} rows={3} onChange={(e) => setMotivo(e.target.value)}
          style={{ width: "100%", marginTop: 8, padding: 10, border: "1px solid var(--border)", borderRadius: 6 }} />
      </label>
      {!motivo.trim() && <p className="hint" style={{ margin: 0 }}>Escribí el motivo para poder reasignar.</p>}
      <Aviso texto={error} error />
      <div className="staff-actions">
        <Button className="btn btn-primary" disabled={!motivo.trim() || enviando} onClick={reasignar}>{enviando ? "Reasignando…" : "Reasignar"}</Button>
        <Button variant="outline" className="staff-secondary" onClick={onCerrar}>Cancelar</Button>
      </div>
    </Ventana>
  );
}

// La foto se descarga con el token y se muestra con una URL local (ver getFotoPedido en api.ts).
function FotoEntrega({ id, sesion }: { id: number; sesion: SesionActiva }) {
  const [url, setUrl] = useState<string | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    let local: string | null = null;
    getFotoPedido(sesion.token, id)
      .then((u) => { local = u; setUrl(u); })
      .catch((err) => setError(sesion.manejarError(err)));
    return () => { if (local) URL.revokeObjectURL(local); };
  }, [id]); // eslint-disable-line react-hooks/exhaustive-deps

  return (
    <div style={{ marginBottom: 30 }}>
      <h3 style={{ fontSize: 18, marginBottom: 12 }}>Foto de la entrega</h3>
      <Aviso texto={error} error />
      {url ? <img src={url} alt="Foto de la entrega" style={{ maxWidth: "100%", maxHeight: 420, borderRadius: 8, border: "1px solid var(--border)" }} />
        : !error && <p className="fsub">Cargando foto…</p>}
    </div>
  );
}

// HU-05: se abre con los datos actuales. El botón se habilita solo si todo es válido y algo cambió.
// Si cambia el peso o las medidas y el repartidor ya no puede llevarlo, el backend lo reasigna.
function ModificarPedido({ pedido, sesion, onCerrar, onListo }: Omit<PropsVentana, "abierta">) {
  const [borrador, setBorrador] = useState(() => borradorDe(pedido));
  const [enviando, setEnviando] = useState(false);
  const [error, setError] = useState("");
  const sinCambios = JSON.stringify(datosDe(borrador)) === JSON.stringify(datosDe(borradorDe(pedido)));
  const falta = queFaltaPedido(borrador) ?? (sinCambios ? "Cambiá algún dato para poder guardar." : null);

  async function guardar() {
    setEnviando(true);
    try {
      const r = await modificarPedido(sesion.token, pedido.id, datosDe(borrador));
      const antes = pedido.repartidor?.id ?? null;
      const ahora = r.repartidor?.id ?? null;
      onListo(
        r.aviso ? `Se guardaron los cambios. ${r.aviso}`
          : ahora !== antes && r.repartidor ? `Se guardaron los cambios y el pedido se asignó a ${r.repartidor.nombre}.`
          : "Se guardaron los cambios.",
      );
    } catch (err) {
      setError(sesion.manejarError(err));
      setEnviando(false);
    }
  }

  return (
    <Ventana abierta titulo={`Modificar el pedido ${pedido.codigo_seguimiento}`}
      descripcion="Si cambiás el peso o las medidas y el repartidor ya no puede llevarlo, se asigna a otro." onCerrar={onCerrar}>
      <div className="fgrid" style={{ maxHeight: "60vh", overflowY: "auto" }}>
        <CamposPedido borrador={borrador} onCambio={setBorrador} />
      </div>
      {falta && <p className="hint" style={{ margin: 0 }}>{falta}</p>}
      <Aviso texto={error} error />
      <div className="staff-actions">
        <Button className="btn btn-primary" disabled={!!falta || enviando} onClick={guardar}>{enviando ? "Guardando…" : "Guardar cambios"}</Button>
        <Button variant="outline" className="staff-secondary" onClick={onCerrar}>Cancelar</Button>
      </div>
    </Ventana>
  );
}
