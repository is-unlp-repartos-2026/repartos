// HU-17: el detalle de un pedido del repartidor (nunca el contenido del paquete).
// Las acciones aparecen SOLO en el estado en que se permiten:
//   "Repartidor asignado" → HU-18 Retirar pedido
//   "En camino"           → HU-20 Confirmar entrega (foto + DNI) y HU-07 Registrar entrega fallida (motivo)
import { useEffect, useState } from "react";
import { Camera, PackageCheck, PackageX } from "lucide-react";
import { Button } from "@/components/ui/button";
import {
  MOTIVOS_FALLO, confirmarEntrega, getPedidoAsignado, registrarEntregaFallida, retirarPedido,
  type DetallePedidoAsignado as Detalle, type MotivoFallo,
} from "@/lib/api";
import { NOMBRE_ESTADO, dniValido, formatearMedidas, soloDigitos } from "@/lib/formato";
import { Aviso, type SesionActiva } from "../comun";

type Props = { id: number; sesion: SesionActiva; onTerminado: (aviso: string) => void };

export function DetallePedidoAsignado({ id, sesion, onTerminado }: Props) {
  const [pedido, setPedido] = useState<Detalle | null>(null);
  const [error, setError] = useState("");
  const [enviando, setEnviando] = useState(false);
  const [accion, setAccion] = useState<"entregar" | "fallida" | null>(null);

  function cargar() {
    getPedidoAsignado(sesion.token, id)
      .then((p) => { setPedido(p); setError(""); })
      .catch((err) => setError(sesion.manejarError(err))); // 404: ya no es suyo (p. ej. se lo reasignaron)
  }
  useEffect(cargar, [id]); // eslint-disable-line react-hooks/exhaustive-deps

  async function retirar() {
    setEnviando(true);
    try {
      await retirarPedido(sesion.token, id);
      cargar(); // queda "En camino" y aparecen las acciones de entrega
    } catch (err) {
      setError(sesion.manejarError(err));
    } finally {
      setEnviando(false);
    }
  }

  if (!pedido) return error ? <Aviso texto={error} error /> : <p className="fsub">Cargando pedido…</p>;

  return (
    <article className="shipment-card" style={{ maxWidth: "none" }}>
      <div className="shipment-card-head">
        <h2 style={{ fontSize: 20 }}>Pedido</h2>
        <span className="staff-status" role="status">{NOMBRE_ESTADO[pedido.estado]}</span>
      </div>
      <dl className="shipment-details">
        <div><dt>Retirar en (origen)</dt><dd>{pedido.origen}</dd></div>
        <div><dt>Entregar en (destino)</dt><dd>{pedido.destino}</dd></div>
        <div><dt>Recibe</dt><dd>{pedido.receptor_nombre}</dd></div>
        <div><dt>DNI de quien recibe</dt><dd>{pedido.receptor_dni}</dd></div>
        <div><dt>Peso</dt><dd>{pedido.peso_kg} kg</dd></div>
        <div><dt>Medidas (alto × ancho × largo)</dt><dd>{formatearMedidas(pedido.alto_cm, pedido.ancho_cm, pedido.largo_cm)}</dd></div>
      </dl>
      <Aviso texto={error} error />

      {pedido.estado === "repartidor_asignado" && (
        <Button className="btn btn-primary staff-submit" disabled={enviando} onClick={retirar}>{enviando ? "Un momento…" : "Retirar pedido"}</Button>
      )}

      {pedido.estado === "en_camino" && (
        <>
          <div className="staff-actions">
            <Button className={accion === "entregar" ? "btn btn-primary" : "staff-secondary"} variant={accion === "entregar" ? "default" : "outline"} onClick={() => setAccion("entregar")}><PackageCheck />Confirmar entrega</Button>
            <Button className={accion === "fallida" ? "btn btn-primary" : "staff-secondary"} variant={accion === "fallida" ? "default" : "outline"} onClick={() => setAccion("fallida")}><PackageX />No se pudo entregar</Button>
          </div>
          {accion === "entregar" && <ConfirmarEntrega id={id} sesion={sesion} onTerminado={onTerminado} />}
          {accion === "fallida" && <EntregaFallida id={id} sesion={sesion} onTerminado={onTerminado} />}
        </>
      )}
    </article>
  );
}

const TIPOS_FOTO = ["image/jpeg", "image/png", "image/webp"];
const MAX_MB_FOTO = 5;

// HU-20: foto Y DNI obligatorios. Si el DNI no coincide con el del pedido, el backend no confirma y lo avisa
// (es un criterio de aceptación). La foto se saca con la cámara del celular.
function ConfirmarEntrega({ id, sesion, onTerminado }: Props) {
  const [foto, setFoto] = useState<File | null>(null);
  const [vistaPrevia, setVistaPrevia] = useState<string | null>(null);
  const [dni, setDni] = useState("");
  const [enviando, setEnviando] = useState(false);
  const [error, setError] = useState("");

  // La URL local de la vista previa se libera cuando cambia la foto o se cierra el formulario.
  useEffect(() => {
    if (!foto) { setVistaPrevia(null); return; }
    const url = URL.createObjectURL(foto);
    setVistaPrevia(url);
    return () => URL.revokeObjectURL(url);
  }, [foto]);

  const problemaFoto = !foto ? "Sacale una foto a la entrega."
    : !TIPOS_FOTO.includes(foto.type) ? "La foto tiene que ser JPG, PNG o WEBP."
    : foto.size > MAX_MB_FOTO * 1024 * 1024 ? `La foto no puede pesar más de ${MAX_MB_FOTO} MB.`
    : null;
  const falta = problemaFoto ?? (dniValido(dni) ? null : "Ingresá el DNI de quien recibe (7 u 8 números).");

  async function confirmar() {
    if (!foto || falta) return;
    setEnviando(true);
    setError("");
    try {
      await confirmarEntrega(sesion.token, id, foto, dni);
      onTerminado("Entrega confirmada. ¡Bien hecho!");
    } catch (err) {
      setError(sesion.manejarError(err));
      setEnviando(false);
    }
  }

  return (
    <div className="form" style={{ marginTop: 20, padding: 0 }}>
      <div className="fgrid">
        <label className="full"><span style={{ display: "flex", alignItems: "center", gap: 6 }}><Camera size={16} />Foto de la entrega</span>
          <input type="file" accept={TIPOS_FOTO.join(",")} capture="environment" onChange={(e) => setFoto(e.target.files?.[0] ?? null)} />
        </label>
        {vistaPrevia && <img src={vistaPrevia} alt="Vista previa de la foto" className="full" style={{ maxHeight: 260, objectFit: "contain", borderRadius: 8 }} />}
        <label className="full">DNI de quien recibe (sin puntos)
          <input inputMode="numeric" value={dni} onChange={(e) => setDni(soloDigitos(e.target.value, 8))} />
        </label>
      </div>
      {falta && <p className="hint">{falta}</p>}
      <Aviso texto={error} error />
      <Button className="btn btn-primary staff-submit" disabled={!!falta || enviando} onClick={confirmar}>{enviando ? "Confirmando…" : "Confirmar entrega"}</Button>
    </div>
  );
}

const LARGO_MAX_ACLARACION = 150;

// HU-07: motivo obligatorio; con "Otro" hay que escribir cuál fue. "Entrega fallida" es final.
function EntregaFallida({ id, sesion, onTerminado }: Props) {
  const [motivo, setMotivo] = useState<MotivoFallo | null>(null);
  const [aclaracion, setAclaracion] = useState("");
  const [enviando, setEnviando] = useState(false);
  const [error, setError] = useState("");

  const falta = !motivo ? "Elegí el motivo." : motivo === "Otro" && !aclaracion.trim() ? "Contá qué pasó." : null;

  async function registrar() {
    if (!motivo || falta) return;
    setEnviando(true);
    setError("");
    try {
      await registrarEntregaFallida(sesion.token, id, motivo, aclaracion);
      onTerminado("Se registró la entrega fallida. El paquete vuelve al comercio.");
    } catch (err) {
      setError(sesion.manejarError(err));
      setEnviando(false);
    }
  }

  return (
    <div className="form" style={{ marginTop: 20, padding: 0 }}>
      <fieldset style={{ border: 0, padding: 0, display: "grid", gap: 10 }}>
        <legend style={{ marginBottom: 10, fontWeight: 600 }}>¿Por qué no se pudo entregar?</legend>
        {MOTIVOS_FALLO.map((m) => (
          <label key={m} style={{ display: "flex", gap: 8, alignItems: "center" }}>
            <input type="radio" name="motivo" checked={motivo === m} onChange={() => setMotivo(m)} />{m}
          </label>
        ))}
      </fieldset>
      <label style={{ display: "block", marginTop: 14 }}>Aclaración {motivo === "Otro" ? "(obligatoria)" : "(opcional)"}
        <textarea value={aclaracion} maxLength={LARGO_MAX_ACLARACION} rows={2} onChange={(e) => setAclaracion(e.target.value)}
          style={{ width: "100%", marginTop: 8, padding: 10, border: "1px solid var(--border)", borderRadius: 6 }} />
      </label>
      {falta && <p className="hint">{falta}</p>}
      <Aviso texto={error} error />
      <Button className="btn btn-primary staff-submit" disabled={!!falta || enviando} onClick={registrar}>{enviando ? "Registrando…" : "Registrar entrega fallida"}</Button>
    </div>
  );
}
