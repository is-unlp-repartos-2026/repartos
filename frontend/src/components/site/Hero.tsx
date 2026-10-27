import hero from "@/assets/hero.jpg";
import { Icon, Eyebrow } from "./Icon";
import { beneficios } from "./data";

export function Hero() {
  return (
    <section className="hero">
      <img src={hero} alt="Camión de SIGER" className="hero-img" width={1920} height={1088} />
      <div className="hero-shade" />
      <div className="container hero-in">
        <Eyebrow>SIGER · Transporte nacional</Eyebrow>
        <h1>Servicios diarios de <em>encomiendas y cargas generales</em></h1>
        <p className="hero-sub">Rapidez, confianza y compromiso en cada entrega.</p>
        <div className="hero-btns">
          <a href="#contacto" className="btn btn-primary">Consultanos por WhatsApp →</a>
          <a href="#cobertura" className="btn btn-ghost">Ver cobertura</a>
        </div>
      </div>
      <div className="hero-bar" />
      <div className="container">
        <div className="benefits">
          {beneficios.map((b) => (
            <div className="benefit" key={b.t}>
              <span className="benefit-ic"><Icon name={b.icon} size={24} /></span>
              <div><strong>{b.t}</strong><p>{b.d}</p></div>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}
