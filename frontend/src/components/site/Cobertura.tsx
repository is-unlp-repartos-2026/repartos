import mapa from "@/assets/mapa-argentina.jpg";
import { Eyebrow } from "./Icon";

export function Cobertura() {
  return (
    <section className="sec sec-dark cobertura" id="cobertura">
      <div className="container cob-grid">
        <div>
          <Eyebrow>Cobertura</Eyebrow>
          <h2 className="h2 big">Llegamos a todo el país.</h2>
          <p className="lead">Realizamos entregas y retiros en toda la República Argentina, coordinando cada envío según su origen, destino y características de la carga.</p>
        </div>
        <div className="map"><img src={mapa} alt="Mapa de cobertura nacional de Argentina" loading="lazy" width={1600} height={912} /></div>
      </div>
    </section>
  );
}
