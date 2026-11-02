// Todas las llamadas al backend pasan por acá.
// La URL sale del archivo .env (VITE_API_URL); si no existe, se usa el backend local.
const API_URL = import.meta.env["VITE_API_URL"] ?? "http://127.0.0.1:8000";

// Error del backend con su código HTTP (401, 404, 409, 422...) y un mensaje para mostrar.
export class ApiError extends Error {
  constructor(public status: number, message: string) {
    super(message);
    this.name = "ApiError";
  }
}

// El backend responde {"detail": "..."} (401, 403, 404, 409) o, en el 422, una lista de errores por campo.
function mensajeDeError(data: unknown): string {
  const detail = (data as { detail?: unknown } | null)?.detail;
  if (typeof detail === "string") return detail;
  if (Array.isArray(detail)) return "Revisá los datos ingresados.";
  return "Ocurrió un error inesperado. Intentá de nuevo.";
}

type Opciones = { method?: string; body?: unknown; token?: string };

// Hace el pedido HTTP y, si el backend responde con error, lanza un ApiError con su mensaje.
async function llamar(ruta: string, opciones: Opciones = {}): Promise<Response> {
  // Un FormData (la foto de la entrega) se manda tal cual: el navegador arma el multipart solo.
  const esFormulario = opciones.body instanceof FormData;
  const headers: Record<string, string> = {};
  if (opciones.body !== undefined && !esFormulario) headers["Content-Type"] = "application/json";
  if (opciones.token) headers["Authorization"] = `Bearer ${opciones.token}`;

  let res: Response;
  try {
    res = await fetch(`${API_URL}${ruta}`, {
      method: opciones.method ?? "GET",
      headers,
      ...(opciones.body !== undefined ? { body: esFormulario ? (opciones.body as FormData) : JSON.stringify(opciones.body) } : {}),
    });
  } catch {
    // fetch solo falla así cuando no llega al servidor (backend apagado, URL mal escrita, sin internet)
    throw new ApiError(0, "No se pudo conectar con el servidor. Intentá de nuevo.");
  }

  if (!res.ok) throw new ApiError(res.status, mensajeDeError(await res.json().catch(() => null)));
  return res;
}

// La mayoría de los endpoints responden JSON.
async function pedir<T>(ruta: string, opciones: Opciones = {}): Promise<T> {
  const res = await llamar(ruta, opciones);
  return (await res.json().catch(() => null)) as T;
}

// --- Tokens guardados en el navegador (la sesión sobrevive a recargar la página) ---

const CLAVE_TOKEN_OPERARIO = "operarioToken";
const CLAVE_TOKEN_REPARTIDOR = "repartidorToken";

export type AlmacenToken = { leer: () => string | null; guardar: (token: string) => void; borrar: () => void };

export const tokenOperario: AlmacenToken = {
  leer: () => localStorage.getItem(CLAVE_TOKEN_OPERARIO),
  guardar: (token) => localStorage.setItem(CLAVE_TOKEN_OPERARIO, token),
  borrar: () => localStorage.removeItem(CLAVE_TOKEN_OPERARIO),
};

export const tokenRepartidor: AlmacenToken = {
  leer: () => localStorage.getItem(CLAVE_TOKEN_REPARTIDOR),
  guardar: (token) => localStorage.setItem(CLAVE_TOKEN_REPARTIDOR, token),
  borrar: () => localStorage.removeItem(CLAVE_TOKEN_REPARTIDOR),
};

// --- Tipos de lo que devuelve el backend ---

export type SesionIniciada = { token: string; tipo: string };
export type OperarioLogueado = { id: number; usuario: string };

export type Estado = "registrado" | "repartidor_asignado" | "en_camino" | "entregado" | "entrega_fallida" | "cancelado";

export type Repartidor = {
  id: number;
  nombre: string;
  dni: string;
  correo: string;
  peso_max_kg: number;
  alto_max_cm: number;
  ancho_max_cm: number;
  largo_max_cm: number;
  habilitado: boolean;
  activo: boolean;
};
export type RepartidorRegistrado = Repartidor & { codigo_acceso: string };
export type DatosNuevoRepartidor = Omit<Repartidor, "id" | "habilitado" | "activo">;
export type Habilitacion = Pick<Repartidor, "peso_max_kg" | "alto_max_cm" | "ancho_max_cm" | "largo_max_cm">;
export type RepartidorDeshabilitado = { repartidor: Repartidor; pedidos_reasignados: number; pedidos_sin_repartidor: number };

export type RepartidorDelPedido = { id: number; nombre: string };

export type DatosNuevoPedido = {
  origen: string;
  destino: string;
  receptor_nombre: string;
  receptor_dni: string;
  peso_kg: number;
  alto_cm: number;
  ancho_cm: number;
  largo_cm: number;
};
export type PedidoRegistrado = DatosNuevoPedido & {
  id: number;
  codigo_seguimiento: string;
  estado: Estado;
  repartidor: RepartidorDelPedido | null;
  aviso: string | null; // cuando quedó sin repartidor
};

export type PedidoEnTablero = {
  id: number;
  codigo_seguimiento: string;
  origen: string;
  destino: string;
  repartidor: RepartidorDelPedido | null;
  desde: string; // cuándo pasó a su estado actual
};
export type Tablero = { registrado: PedidoEnTablero[]; repartidor_asignado: PedidoEnTablero[]; en_camino: PedidoEnTablero[] };

export type DetallePedidoOperario = DatosNuevoPedido & {
  id: number;
  codigo_seguimiento: string;
  estado: Estado;
  repartidor: RepartidorDelPedido | null;
  historial: { estado: Estado; fecha_hora: string; repartidor: RepartidorDelPedido | null; detalle: string | null }[];
  foto_url: string | null; // solo si está entregado
  motivo_fallo: string | null; // solo si la entrega falló
};

export type EstadoActualizado = { id: number; estado: Estado };
export type ResultadoReasignacion = { id: number; estado: Estado; repartidor: RepartidorDelPedido | null; aviso: string | null };

export type JornadaComenzada = { activo: boolean; pedidos_asignados: number };
export type JornadaTerminada = { activo: boolean; pedidos_reasignados: number; pedidos_sin_repartidor: number };

export type PedidoAsignado = { id: number; origen: string; destino: string; estado: Estado; asignado_el: string };
export type DetallePedidoAsignado = DatosNuevoPedido & { id: number; estado: Estado };

// Los mismos 4 motivos que acepta el backend (HU-07).
export const MOTIVOS_FALLO = ["Destinatario ausente", "Dirección incorrecta", "Pedido rechazado", "Otro"] as const;
export type MotivoFallo = (typeof MOTIVOS_FALLO)[number];

export type Seguimiento = {
  codigo_seguimiento: string;
  estado: Estado;
  historial: { estado: Estado; fecha_hora: string }[];
};

// --- Operario: sesión ---

export function loginOperario(usuario: string, contrasena: string) {
  return pedir<SesionIniciada>("/operario/login", { method: "POST", body: { usuario, contrasena } });
}

export function getSesionOperario(token: string) {
  return pedir<OperarioLogueado>("/operario/sesion", { token });
}

// --- Operario: repartidores ---

export function listarRepartidores(token: string) {
  return pedir<Repartidor[]>("/operario/repartidores", { token });
}

export function registrarRepartidor(token: string, datos: DatosNuevoRepartidor) {
  return pedir<RepartidorRegistrado>("/operario/repartidores", { method: "POST", body: datos, token });
}

export function modificarHabilitacion(token: string, id: number, datos: Habilitacion) {
  return pedir<Repartidor>(`/operario/repartidores/${id}/habilitacion`, { method: "PUT", body: datos, token });
}

export function deshabilitarRepartidor(token: string, id: number) {
  return pedir<RepartidorDeshabilitado>(`/operario/repartidores/${id}/deshabilitar`, { method: "POST", token });
}

export function habilitarRepartidor(token: string, id: number) {
  return pedir<Repartidor>(`/operario/repartidores/${id}/habilitar`, { method: "POST", token });
}

// --- Operario: pedidos ---

export function registrarPedido(token: string, datos: DatosNuevoPedido) {
  return pedir<PedidoRegistrado>("/operario/pedidos", { method: "POST", body: datos, token });
}

export function getTablero(token: string) {
  return pedir<Tablero>("/operario/tablero", { token });
}

export function getDetallePedido(token: string, id: number) {
  return pedir<DetallePedidoOperario>(`/operario/pedidos/${id}`, { token });
}

// La foto pide token, así que no se puede poner la URL en un <img>: se descarga y se arma una URL local.
// Quien la usa tiene que liberarla con URL.revokeObjectURL cuando ya no la muestra.
export async function getFotoPedido(token: string, id: number) {
  const res = await llamar(`/operario/pedidos/${id}/foto`, { token });
  return URL.createObjectURL(await res.blob());
}

export function cancelarPedido(token: string, id: number) {
  return pedir<EstadoActualizado>(`/operario/pedidos/${id}/cancelar`, { method: "POST", token });
}

export function reasignarPedido(token: string, id: number, motivo: string) {
  return pedir<ResultadoReasignacion>(`/operario/pedidos/${id}/reasignar`, { method: "POST", body: { motivo }, token });
}

// --- Repartidor ---

export function loginRepartidor(codigo: string) {
  return pedir<SesionIniciada>("/repartidor/login", { method: "POST", body: { codigo } });
}

export function getSesionRepartidor(token: string) {
  return pedir<Repartidor>("/repartidor/sesion", { token });
}

export function comenzarJornada(token: string) {
  return pedir<JornadaComenzada>("/repartidor/jornada/comenzar", { method: "POST", token });
}

export function terminarJornada(token: string) {
  return pedir<JornadaTerminada>("/repartidor/jornada/terminar", { method: "POST", token });
}

export function listarPedidosAsignados(token: string) {
  return pedir<PedidoAsignado[]>("/repartidor/pedidos", { token });
}

export function getPedidoAsignado(token: string, id: number) {
  return pedir<DetallePedidoAsignado>(`/repartidor/pedidos/${id}`, { token });
}

export function retirarPedido(token: string, id: number) {
  return pedir<EstadoActualizado>(`/repartidor/pedidos/${id}/retirar`, { method: "POST", token });
}

export function registrarEntregaFallida(token: string, id: number, motivo: MotivoFallo, aclaracion: string) {
  return pedir<EstadoActualizado>(`/repartidor/pedidos/${id}/entrega-fallida`, {
    method: "POST",
    body: { motivo, aclaracion: aclaracion.trim() || null },
    token,
  });
}

export function confirmarEntrega(token: string, id: number, foto: File, dni: string) {
  const datos = new FormData();
  datos.append("foto", foto);
  datos.append("dni", dni);
  return pedir<EstadoActualizado>(`/repartidor/pedidos/${id}/confirmar-entrega`, { method: "POST", body: datos, token });
}

// --- Cliente final (sin login) ---

export function consultarSeguimiento(codigo: string) {
  return pedir<Seguimiento>(`/seguimiento/${encodeURIComponent(codigo)}`);
}
