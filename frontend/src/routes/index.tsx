import { createFileRoute, Link } from "@tanstack/react-router";
import { Button } from "@/components/ui/button";
import { Truck, ClipboardList } from "lucide-react";
import { Header } from "@/components/site/Header";
import { Hero } from "@/components/site/Hero";
import { Destacados, Servicios } from "@/components/site/Servicios";
import { Cobertura } from "@/components/site/Cobertura";
import { Seguimiento, Contacto, Footer } from "@/components/site/Inferior";

export const Route = createFileRoute("/")({
  head: () => ({
    meta: [
      { title: "SIGER · Encomiendas y cargas generales" },
      { name: "description", content: "Servicios diarios de encomiendas y cargas generales a todo el país." },
      { property: "og:title", content: "SIGER · Encomiendas y cargas generales" },
      { property: "og:description", content: "Servicios diarios de encomiendas y cargas generales a todo el país." },
      { property: "og:type", content: "website" },
      { name: "twitter:card", content: "summary_large_image" },
    ],
  }),
  component: Index,
});

function Index() {
  return (
    <div className="site">
      <Header />
      <main>
        <Hero />
        <div className="staff-entry-band"><div className="container staff-entry"><Button asChild variant="outline" className="staff-secondary"><Link to="/repartidor" target="_blank" rel="noopener noreferrer"><Truck />Soy repartidor</Link></Button><Button asChild variant="outline" className="staff-secondary"><Link to="/operario" target="_blank" rel="noopener noreferrer"><ClipboardList />Operario</Link></Button></div></div>
        <Destacados />
        <Servicios />
        <Cobertura />
        <Seguimiento />
        <Contacto />
      </main>
      <Footer />
    </div>
  );
}
