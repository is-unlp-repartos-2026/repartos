import { createFileRoute } from "@tanstack/react-router";
import { StaffPortal } from "@/components/site/StaffPortal";

export type SeccionOperario = "envios" | "repartidores";

export const Route = createFileRoute("/operario")({
  // La sección va en la URL (/operario?seccion=envios): así el botón "atrás" del navegador vuelve a la anterior.
  // Sin ?seccion se muestra la de repartidores.
  validateSearch: (search: Record<string, unknown>): { seccion?: SeccionOperario } =>
    search["seccion"] === "envios" || search["seccion"] === "repartidores" ? { seccion: search["seccion"] } : {},
  head: () => ({ meta: [
    { title: "Operarios · SIGER" },
    { name: "description", content: "Acceso de demostración para operarios de SIGER y registro de envíos en proceso." },
    { property: "og:title", content: "Operarios · SIGER" },
    { property: "og:description", content: "Acceso de demostración para operarios y registro de envíos en proceso." },
    { property: "og:type", content: "website" }, { name: "twitter:card", content: "summary_large_image" },
  ] }),
  component: () => <StaffPortal role="operario" />,
});