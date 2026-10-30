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
  documentoReceptor: z.string().trim().min(1, "Completá el documento del receptor.").max(20),
  pesoKg: z.coerce.number().min(0.1, "El peso debe ser mayor a 0."),
  dimensiones: z.string().trim().min(1, "Completá las dimensiones del paquete.").max(100),
});
export type ShipmentInput = z.infer<typeof shipmentSchema>;
export type Shipment = ShipmentInput & { guia: string; estado: string; repartidor?: string | undefined };

export const demoShipments: Shipment[] = [
  { guia: "Y7X2-K9M4", origen: "Av. 1 y Calle 47, La Plata", destino: "Av. Corrientes 1200, CABA", destinatario: "Cliente de ejemplo", documentoReceptor: "11222333", pesoKg: 4.5, dimensiones: "35 x 25 x 20 cm", estado: "Pendiente de aceptación", repartidor: "RP01" },
  { guia: "B4W8-P3Q1", origen: "Depósito de ejemplo, Rosario", destino: "Sucursal de ejemplo, Córdoba", destinatario: "Comercio de ejemplo", documentoReceptor: "44555666", pesoKg: 12, dimensiones: "50 x 40 x 30 cm", estado: "Registrado" },
];

export const driverRegistrationSchema = z.object({
  nombre: z.string().trim().min(1, "Ingresá el nombre.").max(100),
  documento: z.string().trim().min(1, "Ingresá el documento.").max(20),
  correo: z.string().email("Ingresá un correo válido.").max(100),
  pesoMaxKg: z.coerce.number().min(1, "Ingresá el peso máximo."),
  dimensionesMax: z.string().trim().min(1, "Ingresá las dimensiones.").max(100),
});

export type DriverToken = {
  token: string;
  nombre: string;
  documento: string;
  correo: string;
  pesoMaxKg: number;
  dimensionesMax: string;
  habilitado: boolean;
  activo: boolean;
};

const TOKEN_CHARS = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789";
export function generateDriverToken(existing: string[], random: () => number = Math.random): string {
  for (;;) {
    const t = Array.from({ length: 4 }, () => TOKEN_CHARS[Math.floor(random() * TOKEN_CHARS.length)]).join("");
    if (!existing.includes(t)) return t;
  }
}

export function generateTrackingCode(existing: string[], random: () => number = Math.random): string {
  for (;;) {
    const t = Array.from({ length: 8 }, () => TOKEN_CHARS[Math.floor(random() * TOKEN_CHARS.length)]).join("");
    const code = `${t.slice(0, 4)}-${t.slice(4)}`;
    if (!existing.includes(code)) return code;
  }
}

export const DEMO_CHANNEL = "siger-demo-staff";
export type DemoMessage =
  | { type: "request" }
  | { type: "sync"; tokens: DriverToken[]; shipments: Shipment[] }
  | { type: "decide"; token: string; guia: string; estado: string }
  | { type: "toggleDisponibilidad"; token: string };