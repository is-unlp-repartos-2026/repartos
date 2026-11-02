import { createFileRoute } from "@tanstack/react-router";
import { RepartidorPortal } from "@/components/personal/repartidor/RepartidorPortal";

export const Route = createFileRoute("/repartidor")({
  // El pedido abierto va en la URL (/repartidor?pedido=12): el "atrás" del celular vuelve a la lista.
  validateSearch: (search: Record<string, unknown>): { pedido?: number } => {
    const pedido = Number(search["pedido"]);
    return Number.isInteger(pedido) && pedido > 0 ? { pedido } : {};
  },
  head: () => ({ meta: [
    { title: "Repartidores · SIGER" },
    { name: "description", content: "App del repartidor de SIGER: jornada y pedidos asignados." },
    { property: "og:title", content: "Repartidores · SIGER" },
    { property: "og:description", content: "App del repartidor de SIGER." },
    { property: "og:type", content: "website" }, { name: "twitter:card", content: "summary_large_image" },
  ] }),
  component: RepartidorPortal,
});