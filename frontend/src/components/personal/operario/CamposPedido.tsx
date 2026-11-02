// Los datos de un pedido: los usan Registrar pedido (HU-04) y Modificar pedido (HU-05).
// Nunca se pide el contenido del paquete. Lo inválido no entra en los campos y `queFalta` dice qué falta
// completar (mientras falte algo, el botón de guardar queda deshabilitado).
import type { DatosNuevoPedido } from "@/lib/api";
import { dniValido, soloDecimal, soloDigitos, validarMedidas } from "@/lib/formato";

const MEDIDAS = [
  ["peso_kg", "Peso (kg)"], ["alto_cm", "Alto (cm)"], ["ancho_cm", "Ancho (cm)"], ["largo_cm", "Largo (cm)"],
] as const;

// Mientras se escribe, todo es texto: se pasa a números recién al enviar.
export type BorradorPedido = Record<keyof DatosNuevoPedido, string>;
export const PEDIDO_VACIO: BorradorPedido = { origen: "", destino: "", receptor_nombre: "", receptor_dni: "", peso_kg: "", alto_cm: "", ancho_cm: "", largo_cm: "" };

export const borradorDe = (p: DatosNuevoPedido): BorradorPedido => ({
  origen: p.origen, destino: p.destino, receptor_nombre: p.receptor_nombre, receptor_dni: p.receptor_dni,
  peso_kg: String(p.peso_kg), alto_cm: String(p.alto_cm), ancho_cm: String(p.ancho_cm), largo_cm: String(p.largo_cm),
});

export const datosDe = (b: BorradorPedido): DatosNuevoPedido => ({
  origen: b.origen.trim(), destino: b.destino.trim(), receptor_nombre: b.receptor_nombre.trim(), receptor_dni: b.receptor_dni,
  peso_kg: Number(b.peso_kg), alto_cm: Number(b.alto_cm), ancho_cm: Number(b.ancho_cm), largo_cm: Number(b.largo_cm),
});

// Las mismas reglas que el backend. Devuelve qué falta completar, o null si está todo bien.
export function queFaltaPedido(d: BorradorPedido): string | null {
  if (!d.origen.trim()) return "Completá el origen.";
  if (!d.destino.trim()) return "Completá el destino.";
  if (!d.receptor_nombre.trim()) return "Completá el nombre de quien recibe.";
  if (!dniValido(d.receptor_dni)) return "El DNI de quien recibe tiene que tener 7 u 8 números.";
  return validarMedidas(d, MEDIDAS);
}

export function CamposPedido({ borrador, onCambio }: { borrador: BorradorPedido; onCambio: (b: BorradorPedido) => void }) {
  const campo = (nombre: keyof BorradorPedido, limpiar: (v: string) => string = (v) => v) => ({
    value: borrador[nombre],
    onChange: (e: { target: { value: string } }) => onCambio({ ...borrador, [nombre]: limpiar(e.target.value) }),
  });

  return <>
    <label>Origen<input maxLength={200} placeholder="Dirección del comercio" {...campo("origen")} /></label>
    <label>Destino<input maxLength={200} placeholder="Dirección de entrega" {...campo("destino")} /></label>
    <label>Nombre de quien recibe<input maxLength={100} {...campo("receptor_nombre")} /></label>
    <label>DNI de quien recibe (sin puntos)<input inputMode="numeric" {...campo("receptor_dni", (v) => soloDigitos(v, 8))} /></label>
    {MEDIDAS.map(([nombre, etiqueta]) => (
      <label key={nombre}>{etiqueta}<input inputMode="decimal" {...campo(nombre, soloDecimal)} /></label>
    ))}
  </>;
}
