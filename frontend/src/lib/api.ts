const API_URL = "http://127.0.0.1:8000";

export async function loginOperario(
  usuario: string,
  contrasena: string
) {
  const res = await fetch(
    `${API_URL}/operario/login`,
    {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        usuario,
        contrasena,
      }),
    }
  );

  if (!res.ok) {
    throw new Error("Login inválido");
  }

  return res.json();
}
