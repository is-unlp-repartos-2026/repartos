// Lo que comparten el panel del operario y la app del repartidor:
// el marco de la pantalla, el manejo de la sesión, el refresco automático y las ventanas de confirmación.
import { useEffect, useRef, useState, type ReactNode } from "react";
import { LogOut } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { Header } from "@/components/site/Header";
import { Footer } from "@/components/site/Inferior";
import { ApiError, type AlmacenToken } from "@/lib/api";

export function Marco({ rol, titulo, onSalir, children }: { rol: string; titulo: string; onSalir?: (() => void) | undefined; children: ReactNode }) {
  return <div className="site staff-page">
    <Header compact />
    <main className="sec sec-white staff-main"><div className="container">
      <div className="staff-heading">
        <div><p className="eyebrow">SIGER · {rol}</p><h1 className="h2">{titulo}</h1></div>
        {onSalir && <Button variant="outline" className="staff-secondary" onClick={onSalir}><LogOut />Salir</Button>}
      </div>
      {children}
    </div></main><Footer compact />
  </div>;
}

// Solo un 401/403 significa que la sesión ya no vale (venció, código revocado o repartidor deshabilitado).
// Si el error es de conexión, la sesión se conserva: el repartidor puede estar sin señal en la calle.
const sesionInvalida = (err: unknown) => err instanceof ApiError && (err.status === 401 || err.status === 403);

// Maneja la sesión guardada en el navegador:
// al abrir la página verifica el token con el backend; si sigue valiendo, entra directo (HU-01 y HU-02).
export function useSesion<T>(almacen: AlmacenToken, verificarToken: (token: string) => Promise<T>) {
  const [usuario, setUsuario] = useState<T | null>(null);
  const [estado, setEstado] = useState<"verificando" | "sin-conexion" | "listo">("verificando");
  const [error, setError] = useState("");

  function verificar() {
    const token = almacen.leer();
    if (!token) { setEstado("listo"); return; }
    setEstado("verificando");
    verificarToken(token)
      .then((u) => { setUsuario(u); setEstado("listo"); })
      .catch((err: Error) => {
        setError(err.message);
        if (sesionInvalida(err)) { almacen.borrar(); setEstado("listo"); } // vuelve al ingreso
        else setEstado("sin-conexion");
      });
  }

  useEffect(verificar, []); // eslint-disable-line react-hooks/exhaustive-deps

  // Después del login: guarda el token y busca los datos de quien entró.
  async function iniciar(token: string) {
    almacen.guardar(token);
    setUsuario(await verificarToken(token));
    setError("");
  }

  function cerrar(mensaje = "") {
    almacen.borrar();
    setUsuario(null);
    setError(mensaje);
  }

  // Para los errores de cualquier pantalla: si la sesión ya no vale, vuelve al ingreso con el aviso;
  // si no, devuelve el mensaje para mostrarlo en esa pantalla (p. ej. un 409 del backend).
  function manejarError(err: unknown): string {
    if (sesionInvalida(err)) {
      cerrar(err instanceof ApiError && err.status === 403 ? err.message : "Tu sesión venció. Ingresá de nuevo.");
      return "";
    }
    return (err as Error).message;
  }

  return { usuario, setUsuario, estado, error, setError, reintentar: verificar, iniciar, cerrar, manejarError, leerToken: almacen.leer };
}

// Pantalla que se ve si no se pudo verificar la sesión guardada porque el backend no responde.
export function SinConexion({ mensaje, onReintentar }: { mensaje: string; onReintentar: () => void }) {
  return <div className="form staff-login">
    <p className="staff-error" role="alert">{mensaje}</p>
    <Button className="btn btn-primary staff-submit" onClick={onReintentar}>Reintentar</Button>
  </div>;
}

// Ejecuta `accion` ahora y después cada `ms` milisegundos (HU-22: "se actualiza solo, sin recargar").
export function useCadaTanto(accion: () => void, ms: number) {
  const ultima = useRef(accion);
  ultima.current = accion;
  useEffect(() => {
    ultima.current();
    const id = setInterval(() => ultima.current(), ms);
    return () => clearInterval(id);
  }, [ms]);
}

// Ventana emergente (para confirmar acciones o pedir un dato, como el motivo de una reasignación).
export function Ventana({ abierta, titulo, descripcion, onCerrar, children }: {
  abierta: boolean; titulo: string; descripcion?: string; onCerrar: () => void; children: ReactNode;
}) {
  return <Dialog open={abierta} onOpenChange={(abrir) => { if (!abrir) onCerrar(); }}>
    <DialogContent>
      <DialogHeader>
        <DialogTitle>{titulo}</DialogTitle>
        {descripcion && <DialogDescription>{descripcion}</DialogDescription>}
      </DialogHeader>
      {children}
    </DialogContent>
  </Dialog>;
}

// Aviso de resultado ("Pedido cancelado", "Se reasignaron 2 pedidos"...) o de error.
export function Aviso({ texto, error = false }: { texto: string; error?: boolean }) {
  if (!texto) return null;
  return <p className={error ? "staff-error" : "demo-notice"} role={error ? "alert" : "status"} style={{ margin: "16px 0" }}>{texto}</p>;
}

// Lo que reciben las pantallas de adentro (ya logueado): el token y cómo manejar un error.
export type SesionActiva = { token: string; manejarError: (err: unknown) => string };
