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

// Hoy en formato AAAA-MM-DD (el de los <input type="date">), según el reloj del dispositivo.
export const hoyISO = () => new Date().toLocaleDateString("en-CA");

// "2026-03-10" → "10/03/2026"
export const formatearDia = (iso: string) => iso.split("-").reverse().join("/");

// 37.5 → "38 min" · 95 → "1 h 35 min" · 3000 → "2 d 2 h"
export function formatearMinutos(minutos: number | null): string {
  if (minutos === null) return "Sin datos";
  const total = Math.round(minutos);
  if (total < 60) return `${total} min`;
  const horas = Math.floor(total / 60);
  if (horas < 24) return `${horas} h ${String(total % 60).padStart(2, "0")} min`;
  return `${Math.floor(horas / 24)} d ${horas % 24} h`;
}

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
