const API_URL = "http://127.0.0.1:8000";

export class CredencialesInvalidasError extends Error {
  constructor(message?: string) {
    super(message);
    this.name = "CredencialesInvalidasError";
  }
}

export async function loginOperario(usuario: string, contrasena: string) {
  const response = await fetch(`${API_URL}/operario/login`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ usuario, contrasena }),
  });
  if (!response.ok) throw new CredencialesInvalidasError("Credenciales inválidas");
  return response.json();
}

export async function loginRepartidor(codigo: string) {
  const response = await fetch(`${API_URL}/repartidor/login`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ codigo }),
  });
  
  if (!response.ok) {
    const err = await response.json().catch(() => ({}));
    throw new Error(err.detail || "Código inválido o acceso denegado");
  }
  return response.json();
}

export async function getSesionRepartidor(token: string) {
  const response = await fetch(`${API_URL}/repartidor/sesion`, {
    method: "GET",
    headers: { "Authorization": `Bearer ${token}` },
  });
  
  if (!response.ok) {
    throw new Error("Sesión vencida o repartidor deshabilitado");
  }
  return response.json();
}