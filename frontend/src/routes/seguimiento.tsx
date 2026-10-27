import { createFileRoute, Link } from "@tanstack/react-router";
import { Header } from "@/components/site/Header";
import { Footer } from "@/components/site/Inferior";
import { Eyebrow } from "@/components/site/Icon";

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

function SeguimientoPage() {
  const { guia } = Route.useSearch();

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
              <h3>Próximamente</h3>
              <p className="fsub">
                Acá se mostrará el estado del pedido con su recorrido y fechas. Cuando definas los estados del envío y la base de datos
                a utilizar, esta página se conectará para mostrar la información real.
              </p>
              <Link to="/" className="btn btn-primary" style={{ display: "inline-block", marginTop: 18 }}>Volver al inicio</Link>
            </div>
          </div>
        </section>
      </main>
      <Footer compact />
    </div>
  );
}
