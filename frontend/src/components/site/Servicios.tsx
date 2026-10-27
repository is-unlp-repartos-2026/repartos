import c1 from "@/assets/card-1.jpg";
import c2 from "@/assets/card-2.jpg";
import c3 from "@/assets/card-3.jpg";
import c4 from "@/assets/card-4.jpg";
import { Icon, Eyebrow } from "./Icon";
import { servicios } from "./data";

const destacados = [
  { img: c1, icon: "calendar", t: "Salidas diarias", d: "Conexiones programadas entre nuestras bases y las zonas de cobertura." },
  { img: c2, icon: "clock", t: "Envíos express", d: "Entregas rápidas en 24 o 48 horas, según el origen y el destino." },
  { img: c4, icon: "headset", t: "Atención personalizada", d: "Coordinación directa para cada envío y necesidad." },
];

export function Destacados() {
  return (
    <section className="sec sec-cream destacados" id="servicios">
      <div className="container">
        <div className="split-head">
          <div>
            <Eyebrow>Servicios destacados</Eyebrow>
            <h2 className="h2">Una solución para cada tipo de traslado.</h2>
          </div>
          <p className="lead">Cuatro formas de acompañar tus envíos, con atención directa y una operación adaptada a cada necesidad.</p>
        </div>
        <div className="grid3">
          {destacados.map((c, i) => (
            <article className="fcard" key={c.t}>
              <div className="fcard-img"><img src={c.img} alt={c.t} loading="lazy" width={1056} height={640} /></div>
              <span className="fcard-ic"><Icon name={c.icon} size={20} /></span>
              <div className="fcard-body">
                <span className="num">0{i + 1}</span>
                <h3>{c.t}</h3>
                <p>{c.d}</p>
                <a href="#" className="more">Más información →</a>
              </div>
            </article>
          ))}
        </div>
      </div>
    </section>
  );
}

export function Servicios() {
  return (
    <section className="sec sec-cream servicios">
      <div className="container">
        <Eyebrow>Nuestros servicios</Eyebrow>
        <h2 className="h2 narrow">Soluciones para cada tipo de traslado.</h2>
        <p className="lead narrow">Coordinamos envíos particulares, operaciones comerciales y servicios especiales según origen, destino, volumen y urgencia.</p>
        <div className="grid3">
          {servicios.map((s, i) => (
            <article className="scard" key={s.t}>
              <span className="scard-num">0{i + 1}</span>
              <h3>{s.t}</h3>
              <p>{s.d}</p>
            </article>
          ))}
        </div>
      </div>
    </section>
  );
}
