// HU-04: el operario registra un pedido. El backend genera el código de seguimiento y lo asigna
// automáticamente a un repartidor apto; si no hay ninguno, queda "Registrado" con un aviso.
// Nunca se pide el contenido del paquete. El botón queda deshabilitado hasta que todo sea válido.
import { useState, type FormEvent } from "react";
import { PackagePlus } from "lucide-react";
import { Button } from "@/components/ui/button";
import { registrarPedido, type PedidoRegistrado } from "@/lib/api";
import { NOMBRE_ESTADO, dniValido, soloDecimal, soloDigitos, validarMedidas } from "@/lib/formato";
import { Aviso, type SesionActiva } from "../comun";

const MEDIDAS = [
  ["peso_kg", "Peso (kg)"], ["alto_cm", "Alto (cm)"], ["ancho_cm", "Ancho (cm)"], ["largo_cm", "Largo (cm)"],
] as const;

type Borrador = { origen: string; destino: string; receptor_nombre: string; receptor_dni: string; peso_kg: string; alto_cm: string; ancho_cm: string; largo_cm: string };
const VACIO: Borrador = { origen: "", destino: "", receptor_nombre: "", receptor_dni: "", peso_kg: "", alto_cm: "", ancho_cm: "", largo_cm: "" };

// Las mismas reglas que el backend. Devuelve qué falta completar, o null si está todo bien.
function queFalta(d: Borrador): string | null {
  if (!d.origen.trim()) return "Completá el origen.";
  if (!d.destino.trim()) return "Completá el destino.";
  if (!d.receptor_nombre.trim()) return "Completá el nombre de quien recibe.";
  if (!dniValido(d.receptor_dni)) return "El DNI de quien recibe tiene que tener 7 u 8 números.";
  return validarMedidas(d, MEDIDAS);
}

export function RegistrarPedido({ sesion, onAbrir }: { sesion: SesionActiva; onAbrir: (id: number) => void }) {
  const [borrador, setBorrador] = useState<Borrador>(VACIO);
  const [enviando, setEnviando] = useState(false);
  const [error, setError] = useState("");
  const [registrado, setRegistrado] = useState<PedidoRegistrado | null>(null);
  const falta = queFalta(borrador);

  const campo = (nombre: keyof Borrador, limpiar: (v: string) => string = (v) => v) =>
    ({ value: borrador[nombre], onChange: (e: { target: { value: string } }) => setBorrador((b) => ({ ...b, [nombre]: limpiar(e.target.value) })) });

  async function registrar(e: FormEvent) {
    e.preventDefault();
    if (falta || enviando) return;
    setEnviando(true);
    setError("");
    setRegistrado(null);
    try {
      setRegistrado(await registrarPedido(sesion.token, {
        origen: borrador.origen.trim(),
        destino: borrador.destino.trim(),
        receptor_nombre: borrador.receptor_nombre.trim(),
        receptor_dni: borrador.receptor_dni,
        peso_kg: Number(borrador.peso_kg),
        alto_cm: Number(borrador.alto_cm),
        ancho_cm: Number(borrador.ancho_cm),
        largo_cm: Number(borrador.largo_cm),
      }));
      setBorrador(VACIO);
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
        <label>Origen<input maxLength={200} placeholder="Dirección del comercio" {...campo("origen")} /></label>
        <label>Destino<input maxLength={200} placeholder="Dirección de entrega" {...campo("destino")} /></label>
        <label>Nombre de quien recibe<input maxLength={100} {...campo("receptor_nombre")} /></label>
        <label>DNI de quien recibe (sin puntos)<input inputMode="numeric" {...campo("receptor_dni", (v) => soloDigitos(v, 8))} /></label>
        {MEDIDAS.map(([nombre, etiqueta]) => (
          <label key={nombre}>{etiqueta}<input inputMode="decimal" {...campo(nombre, soloDecimal)} /></label>
        ))}
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
