import { createFileRoute } from "@tanstack/react-router";
import { OperarioPortal, SECCIONES_OPERARIO, type SeccionOperario } from "@/components/personal/operario/OperarioPortal";

export const Route = createFileRoute("/operario")({
  // La sección y el pedido abierto van en la URL (/operario?seccion=tablero&pedido=12):
  // así el botón "atrás" del navegador vuelve a la pantalla anterior. Lo que no sea válido se ignora.
  validateSearch: (search: Record<string, unknown>) => {
    const r: { seccion?: SeccionOperario; pedido?: number } = {};
    const seccion = SECCIONES_OPERARIO.find((x) => x === search["seccion"]);
    if (seccion) r.seccion = seccion;
    const pedido = Number(search["pedido"]);
    if (Number.isInteger(pedido) && pedido > 0) r.pedido = pedido;
    return r;
  },
  head: () => ({ meta: [
    { title: "Operarios · SIGER" },
    { name: "description", content: "Panel del operario de SIGER: pedidos en curso, registro de pedidos y repartidores." },
    { property: "og:title", content: "Operarios · SIGER" },
    { property: "og:description", content: "Panel del operario de SIGER." },
    { property: "og:type", content: "website" }, { name: "twitter:card", content: "summary_large_image" },
  ] }),
  component: OperarioPortal,
});