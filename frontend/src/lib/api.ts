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

async function pedir<T>(ruta: string, opciones: { method?: string; body?: unknown; token?: string } = {}): Promise<T> {
  const headers: Record<string, string> = {};
  if (opciones.body !== undefined) headers["Content-Type"] = "application/json";
  if (opciones.token) headers["Authorization"] = `Bearer ${opciones.token}`;

  let res: Response;
  try {
    res = await fetch(`${API_URL}${ruta}`, {
      method: opciones.method ?? "GET",
      headers,
      ...(opciones.body !== undefined ? { body: JSON.stringify(opciones.body) } : {}),
    });
  } catch {
    // fetch solo falla así cuando no llega al servidor (backend apagado, URL mal escrita, sin internet)
    throw new ApiError(0, "No se pudo conectar con el servidor. Intentá de nuevo.");
  }

  const data = await res.json().catch(() => null);
  if (!res.ok) throw new ApiError(res.status, mensajeDeError(data));
  return data as T;
}

// --- Tokens guardados en el navegador (la sesión sobrevive a recargar la página) ---

const CLAVE_TOKEN_OPERARIO = "operarioToken";
const CLAVE_TOKEN_REPARTIDOR = "repartidorToken";

export const tokenOperario = {
  leer: () => localStorage.getItem(CLAVE_TOKEN_OPERARIO),
  guardar: (token: string) => localStorage.setItem(CLAVE_TOKEN_OPERARIO, token),
  borrar: () => localStorage.removeItem(CLAVE_TOKEN_OPERARIO),
};

export const tokenRepartidor = {
  leer: () => localStorage.getItem(CLAVE_TOKEN_REPARTIDOR),
  guardar: (token: string) => localStorage.setItem(CLAVE_TOKEN_REPARTIDOR, token),
  borrar: () => localStorage.removeItem(CLAVE_TOKEN_REPARTIDOR),
};

// --- Tipos de lo que devuelve el backend ---

export type SesionIniciada = { token: string; tipo: string };
export type OperarioLogueado = { id: number; usuario: string };

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

export type Seguimiento = {
  codigo_seguimiento: string;
  estado: string;
  historial: { estado: string; fecha_hora: string }[];
};

// --- Operario ---

export function loginOperario(usuario: string, contrasena: string) {
  return pedir<SesionIniciada>("/operario/login", { method: "POST", body: { usuario, contrasena } });
}

export function getSesionOperario(token: string) {
  return pedir<OperarioLogueado>("/operario/sesion", { token });
}

export function listarRepartidores(token: string) {
  return pedir<Repartidor[]>("/operario/repartidores", { token });
}

export function registrarRepartidor(token: string, datos: DatosNuevoRepartidor) {
  return pedir<RepartidorRegistrado>("/operario/repartidores", { method: "POST", body: datos, token });
}

// --- Repartidor ---

export function loginRepartidor(codigo: string) {
  return pedir<SesionIniciada>("/repartidor/login", { method: "POST", body: { codigo } });
}

export function getSesionRepartidor(token: string) {
  return pedir<Repartidor>("/repartidor/sesion", { token });
}

// --- Cliente final (sin login) ---

export function consultarSeguimiento(codigo: string) {
  return pedir<Seguimiento>(`/seguimiento/${encodeURIComponent(codigo)}`);
}
