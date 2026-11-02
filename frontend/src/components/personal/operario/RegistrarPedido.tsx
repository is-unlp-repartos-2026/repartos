// HU-04: el operario registra un pedido. El backend genera el código de seguimiento y lo asigna
// automáticamente a un repartidor apto; si no hay ninguno, queda "Registrado" con un aviso.
// Nunca se pide el contenido del paquete. El botón queda deshabilitado hasta que todo sea válido.
import { useState, type FormEvent } from "react";
import { PackagePlus } from "lucide-react";
import { Button } from "@/components/ui/button";
import { registrarPedido, type PedidoRegistrado } from "@/lib/api";
import { NOMBRE_ESTADO } from "@/lib/formato";
import { Aviso, type SesionActiva } from "../comun";
import { CamposPedido, PEDIDO_VACIO, datosDe, queFaltaPedido, type BorradorPedido } from "./CamposPedido";

export function RegistrarPedido({ sesion, onAbrir }: { sesion: SesionActiva; onAbrir: (id: number) => void }) {
  const [borrador, setBorrador] = useState<BorradorPedido>(PEDIDO_VACIO);
  const [enviando, setEnviando] = useState(false);
  const [error, setError] = useState("");
  const [registrado, setRegistrado] = useState<PedidoRegistrado | null>(null);
  const falta = queFaltaPedido(borrador);

  async function registrar(e: FormEvent) {
    e.preventDefault();
    if (falta || enviando) return;
    setEnviando(true);
    setError("");
    setRegistrado(null);
    try {
      setRegistrado(await registrarPedido(sesion.token, datosDe(borrador)));
      setBorrador(PEDIDO_VACIO);
    } catch (err) {
      setError(sesion.manejarError(err));
    } finally {
      setEnviando(false);
    }
  }

  return (
    <section className="form shipment-create" style={{ padding: 24 }}>
      <h2>Registrar pedido</h2>
      {registrado && <Resultado pedido={registrado} onAbrir={onAbrir} />}
      <form className="fgrid" onSubmit={registrar} noValidate>
        <CamposPedido borrador={borrador} onCambio={setBorrador} />
        <div className="full" style={{ marginTop: 12 }}>
          <Aviso texto={error} error />
          {falta && <p className="hint" style={{ marginTop: 0 }}>{falta}</p>}
          <Button type="submit" className="btn btn-primary" disabled={!!falta || enviando}><PackagePlus />{enviando ? "Registrando…" : "Registrar pedido"}</Button>
        </div>
      </form>
    </section>
  );
}

// Muestra el código de seguimiento (para pasárselo al comercio) y cómo quedó la asignación.
function Resultado({ pedido, onAbrir }: { pedido: PedidoRegistrado; onAbrir: (id: number) => void }) {
  return (
    <div className="demo-notice" role="status" style={{ marginTop: 0, borderLeftColor: pedido.repartidor ? "var(--m-orange)" : "var(--m-red)" }}>
      <strong>Pedido registrado.</strong> Código de seguimiento:{" "}
      <strong style={{ fontSize: 20, letterSpacing: "0.15em" }}>{pedido.codigo_seguimiento}</strong>
      <br />
      Estado: <strong>{NOMBRE_ESTADO[pedido.estado]}</strong>
      {pedido.repartidor && <> · Asignado a <strong>{pedido.repartidor.nombre}</strong></>}
      {pedido.aviso && <><br /><span style={{ color: "var(--m-red)" }}>{pedido.aviso}</span></>}
      <br />
      <Button variant="link" style={{ padding: 0, height: "auto" }} onClick={() => onAbrir(pedido.id)}>Ver detalle del pedido</Button>
    </div>
  );
}
