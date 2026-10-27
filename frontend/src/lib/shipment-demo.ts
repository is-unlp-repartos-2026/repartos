import { z } from "zod";

export const trackingGuideSchema = z.string().trim().min(1, "Ingresá el número de guía.").max(100, "La guía es demasiado larga.");
export const demoLoginSchema = z.object({
  usuario: z.string().trim().min(1, "Ingresá tu usuario.").max(100),
  password: z.string().min(1, "Ingresá tu contraseña.").max(128),
});
export const shipmentSchema = z.object({
  origen: z.string().trim().min(1, "Completá el origen.").max(200),
  destino: z.string().trim().min(1, "Completá el destino.").max(200),
  destinatario: z.string().trim().min(1, "Completá el destinatario.").max(100),
  telefono: z.string().trim().regex(/^\d{1,20}$/, "Ingresá un teléfono de hasta 20 números."),
  detalle: z.string().trim().min(1, "Completá el detalle del pedido.").max(1000),
});
export type ShipmentInput = z.infer<typeof shipmentSchema>;
export type Shipment = ShipmentInput & { guia: string; estado: string };
export const demoShipments: Shipment[] = [
  { guia: "DEMO-001", origen: "Av. 1 y Calle 47, La Plata", destino: "Av. Corrientes 1200, CABA", destinatario: "Cliente de ejemplo", telefono: "1100001234", detalle: "2 cajas de artículos de librería. Entrega en recepción.", estado: "Pendiente de aceptación" },
  { guia: "DEMO-002", origen: "Depósito de ejemplo, Rosario", destino: "Sucursal de ejemplo, Córdoba", destinatario: "Comercio de ejemplo", telefono: "1100005678", detalle: "3 bultos de indumentaria.", estado: "En tránsito" },
];