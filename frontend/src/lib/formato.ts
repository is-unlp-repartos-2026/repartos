// Funciones chicas para mostrar datos y limpiar lo que se escribe en los formularios.
import type { Estado } from "./api";

export const NOMBRE_ESTADO: Record<Estado, string> = {
  registrado: "Registrado",
  repartidor_asignado: "Repartidor asignado",
  en_camino: "En camino",
  entregado: "Entregado",
  entrega_fallida: "Entrega fallida",
  cancelado: "Cancelado",
};

export const formatearFecha = (iso: string) =>
  new Date(iso).toLocaleString("es-AR", { dateStyle: "short", timeStyle: "short" });

export const formatearMedidas = (alto: number, ancho: number, largo: number) => `${alto} × ${ancho} × ${largo} cm`;

// --- Limpieza mientras se escribe: lo inválido directamente no entra en el campo ---

// Solo números (DNI): "38.123.456" → "38123456".
export const soloDigitos = (valor: string, maximo: number) => valor.replace(/\D/g, "").slice(0, maximo);

// Solo dígitos y un único punto decimal (acepta coma y la pasa a punto): no se puede escribir "-5" ni "1e3".
export const soloDecimal = (valor: string) => valor.replace(",", ".").replace(/[^\d.]/g, "").replace(/(\..*)\./g, "$1");

// --- Validaciones: devuelven qué falta (para mostrarlo junto al botón deshabilitado) o null ---

export const dniValido = (dni: string) => /^\d{7,8}$/.test(dni);
export const correoValido = (correo: string) => /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(correo.trim());

// Peso y medidas: las cuatro tienen que ser números mayores a 0.
export function validarMedidas<C extends string>(datos: Record<C, string>, campos: readonly (readonly [C, string])[]): string | null {
  for (const [campo, etiqueta] of campos) {
    if (!(Number(datos[campo]) > 0)) return `${etiqueta}: tiene que ser un número mayor a 0.`;
  }
  return null;
}
