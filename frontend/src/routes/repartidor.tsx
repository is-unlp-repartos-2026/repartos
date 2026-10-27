import { createFileRoute } from "@tanstack/react-router";
import { StaffPortal } from "@/components/site/StaffPortal";

export const Route = createFileRoute("/repartidor")({
  head: () => ({ meta: [
    { title: "Repartidores · SIGER" },
    { name: "description", content: "Acceso de demostración para repartidores de SIGER y sus envíos asignados." },
    { property: "og:title", content: "Repartidores · SIGER" },
    { property: "og:description", content: "Acceso de demostración para repartidores y sus envíos asignados." },
    { property: "og:type", content: "website" }, { name: "twitter:card", content: "summary_large_image" },
  ] }),
  component: () => <StaffPortal role="repartidor" />,
});