import { createFileRoute } from "@tanstack/react-router";
import { StaffPortal } from "@/components/site/StaffPortal";

export const Route = createFileRoute("/operario")({
  head: () => ({ meta: [
    { title: "Operarios · SIGER" },
    { name: "description", content: "Acceso de demostración para operarios de SIGER y registro de envíos en proceso." },
    { property: "og:title", content: "Operarios · SIGER" },
    { property: "og:description", content: "Acceso de demostración para operarios y registro de envíos en proceso." },
    { property: "og:type", content: "website" }, { name: "twitter:card", content: "summary_large_image" },
  ] }),
  component: () => <StaffPortal role="operario" />,
});