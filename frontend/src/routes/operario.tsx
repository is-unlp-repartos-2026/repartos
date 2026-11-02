import { createFileRoute } from "@tanstack/react-router";
import { OperarioPortal, SECCIONES_OPERARIO, type BusquedaOperario } from "@/components/personal/operario/OperarioPortal";
import type { Estado } from "@/lib/api";
import { NOMBRE_ESTADO } from "@/lib/formato";

export const Route = createFileRoute("/operario")({
  // La sección, el pedido abierto y los filtros van en la URL (/operario?seccion=historial&pedido=12):
  // así el botón "atrás" del navegador vuelve a la pantalla anterior. Lo que no sea válido se ignora.
  validateSearch: (search: Record<string, unknown>): BusquedaOperario => {
    const r: BusquedaOperario = {};
    const seccion = SECCIONES_OPERARIO.find((x) => x === search["seccion"]);
    if (seccion) r.seccion = seccion;
    const pedido = Number(search["pedido"]);
    if (Number.isInteger(pedido) && pedido > 0) r.pedido = pedido;
    for (const clave of ["desde", "hasta"] as const) {
      const fecha = search[clave];
      if (typeof fecha === "string" && /^\d{4}-\d{2}-\d{2}$/.test(fecha)) r[clave] = fecha;
    }
    const estado = (Object.keys(NOMBRE_ESTADO) as Estado[]).find((x) => x === search["estado"]);
    if (estado) r.estado = estado;
    const repartidor = Number(search["repartidor"]);
    if (Number.isInteger(repartidor) && repartidor > 0) r.repartidor = repartidor;
    return r;
  },
  head: () => ({ meta: [
    { title: "Operarios · SIGER" },
    { name: "description", content: "Panel del operario de SIGER: pedidos en curso, registro, historial, reportes y repartidores." },
    { property: "og:title", content: "Operarios · SIGER" },
    { property: "og:description", content: "Panel del operario de SIGER." },
    { property: "og:type", content: "website" }, { name: "twitter:card", content: "summary_large_image" },
  ] }),
  component: OperarioPortal,
});