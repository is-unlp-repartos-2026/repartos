import { useEffect, useState } from "react";
import { createFileRoute, Link } from "@tanstack/react-router";
import { Header } from "@/components/site/Header";
import { Footer } from "@/components/site/Inferior";
import { Eyebrow } from "@/components/site/Icon";
import { ApiError, consultarSeguimiento, type Seguimiento } from "@/lib/api";

export const Route = createFileRoute("/seguimiento")({
  validateSearch: (search: Record<string, unknown>) => ({
    guia: typeof search["guia"] === "string" ? search["guia"] : "",
  }),
  head: () => ({
    meta: [
      { title: "Seguimiento de envíos · SIGER" },
      { name: "description", content: "Consultá el estado de tu envío con el número de guía." },
      { property: "og:title", content: "Seguimiento de envíos · SIGER" },
      { property: "og:description", content: "Consultá el estado de tu envío con el número de guía." },
      { property: "og:type", content: "website" },
      { name: "twitter:card", content: "summary_large_image" },
    ],
  }),
  component: SeguimientoPage,
});

const formatearEstado = (estado: string) => {
  const texto = estado.replace(/_/g, " ");
  return texto.charAt(0).toUpperCase() + texto.slice(1);
};

const formatearFecha = (iso: string) =>
  new Date(iso).toLocaleString("es-AR", { dateStyle: "short", timeStyle: "short" });

function SeguimientoPage() {
  const { guia } = Route.useSearch();
  const [datos, setDatos] = useState<Seguimiento | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [cargando, setCargando] = useState(false);

  useEffect(() => {
    if (!guia) return;
    let cancelado = false;
    setCargando(true);
    setError(null);
    setDatos(null);

    consultarSeguimiento(guia.trim())
      .then((d) => {
        if (!cancelado) setDatos(d);
      })
      .catch((err) => {
        if (cancelado) return;
        setError(
          err instanceof ApiError && err.status === 404
            ? "No encontramos ningún envío con ese número de guía."
            : "No pudimos consultar el envío. Intentá de nuevo en unos minutos.",
        );
      })
      .finally(() => {
        if (!cancelado) setCargando(false);
      });

    return () => {
      cancelado = true;
    };
  }, [guia]);

  return (
    <div className="site">
      <Header compact />
      <main>
        <section className="sec sec-white">
          <div className="container">
            <Eyebrow>Seguimiento</Eyebrow>
            <h1 className="h2 big">Estado de tu envío.</h1>
            {guia ? (
              <p className="lead">Guía consultada: <strong>{guia}</strong></p>
            ) : (
              <p className="lead">No ingresaste un número de guía. Podés consultar nuevamente desde la página principal.</p>
            )}
            <div className="form" style={{ marginTop: 32 }}>
              {cargando && <p className="fsub">Consultando el estado de tu envío...</p>}
              {error && <p className="fsub">{error}</p>}
              {datos && (
                <>
                  <h3>Estado actual: {formatearEstado(datos.estado)}</h3>
                  <ul style={{ marginTop: 18, paddingLeft: 18 }}>
                    {datos.historial.map((h, i) => (
                      <li key={i}>
                        <strong>{formatearEstado(h.estado)}</strong> — {formatearFecha(h.fecha_hora)}
                      </li>
                    ))}
                  </ul>
                </>
              )}
              <Link to="/" className="btn btn-primary" style={{ display: "inline-block", marginTop: 18 }}>Volver al inicio</Link>
            </div>
          </div>
        </section>
      </main>
      <Footer compact />
    </div>
  );
}