const API_URL = "http://127.0.0.1:8000";

export class CredencialesInvalidasError extends Error {}

export async function loginOperario(
  usuario: string,
  contrasena: string
): Promise<{ token: string; tipo: string }> {
  const res = await fetch(`${API_URL}/operario/login`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ usuario, contrasena }),
  });

  if (res.status === 401) throw new CredencialesInvalidasError();
  if (!res.ok) throw new Error(`Error del servidor (${res.status})`);
  return res.json();
}