import { useState, type ChangeEvent, type FormEvent } from "react";
import { z } from "zod";
import { Eyebrow } from "./Icon";
import { nav } from "./data";
import { trackingGuideSchema } from "@/lib/shipment-demo";
import { Button } from "@/components/ui/button";

const soloTexto = (campo: string) =>
  z
    .string()
    .trim()
    .min(1, `Completá ${campo}.`)
    .regex(/^[^\d]+$/, `${campo} no puede contener números.`)
    .max(100, `${campo} es demasiado largo.`);

const consultaSchema = z.object({
  nombre: soloTexto("el nombre y apellido"),
  empresa: soloTexto("la empresa o comercio"),
  telefono: z
    .string()
    .trim()
    .min(1, "Completá el teléfono.")
    .regex(/^\d+$/, "El teléfono solo puede tener números.")
    .max(20, "El teléfono es demasiado largo."),
  origen: soloTexto("el origen del envío"),
  destino: soloTexto("el destino"),
  detalle: z.string().trim().min(1, "Contanos qué necesitás enviar.").max(1000, "El detalle es demasiado largo."),
});

type Consulta = z.infer<typeof consultaSchema>;
type Errores = Partial<Record<keyof Consulta, string>>;

// Número de WhatsApp que recibe las consultas (formato internacional, sin +).
const WHATSAPP_CONSULTAS = "5493446505697";

export function Seguimiento() {
  const [guia, setGuia] = useState("");
  const [errorGuia, setErrorGuia] = useState("");

  const abrirSeguimiento = (e: FormEvent) => {
    e.preventDefault();
    const resultado = trackingGuideSchema.safeParse(guia);
    if (!resultado.success) {
      setErrorGuia(resultado.error.issues[0]?.message ?? "Ingresá el número de guía.");
      return;
    }
    setErrorGuia("");
    const url = `/seguimiento?guia=${encodeURIComponent(resultado.data)}`;
    window.open(url, "_blank", "noopener,noreferrer");
  };

  return (
    <section className="sec sec-white" id="seguimiento">
      <div className="container contact-grid">
        <div>
          <Eyebrow>Seguimiento</Eyebrow>
          <h2 className="h2 big">Consultar estado de mi envío.</h2>
          <p className="lead">Ingresá el número de guía o seguimiento para conocer en qué etapa se encuentra tu envío.</p>
        </div>
        <form className="form" onSubmit={abrirSeguimiento} noValidate>
          <h3>Seguí tu envío</h3>
          <p className="fsub">El número figura en el comprobante entregado al despachar.</p>
          <div className="fgrid">
            <label className="full">Número de guía<input required maxLength={100} aria-invalid={!!errorGuia} aria-describedby={errorGuia ? "guia-error" : undefined} placeholder="Ej: 000123456" value={guia} onChange={(e) => setGuia(e.target.value)} />{errorGuia && <span className="err" role="alert" id="guia-error">{errorGuia}</span>}</label>
          </div>
          <p className="hint">Si tenés dudas, comunicate con nuestra Casa Central.</p>
          <Button type="submit" className="btn btn-primary">Consultar estado</Button>
        </form>
      </div>
    </section>
  );
}

export function Contacto() {
  const [valores, setValores] = useState<Consulta>({ nombre: "", empresa: "", telefono: "", origen: "", destino: "", detalle: "" });
  const [errores, setErrores] = useState<Errores>({});

  const set =
    (campo: keyof Consulta) =>
    (e: ChangeEvent<HTMLInputElement | HTMLTextAreaElement>) =>
      setValores((v) => ({ ...v, [campo]: e.target.value }));

  const enviar = (e: FormEvent) => {
    e.preventDefault();
    const res = consultaSchema.safeParse(valores);
    if (!res.success) {
      const errs: Errores = {};
      for (const issue of res.error.issues) {
        const campo = issue.path[0] as keyof Consulta;
        if (!errs[campo]) errs[campo] = issue.message;
      }
      setErrores(errs);
      return;
    }
    setErrores({});
    const v = res.data;
    const mensaje = `${v.nombre} de la Empresa o Comercio: ${v.empresa}.\nTel: ${v.telefono}.\nOrigen: ${v.origen}\nDestino: ${v.destino}\nDetalle de la Carga: ${v.detalle}`;
    window.open(`https://wa.me/${WHATSAPP_CONSULTAS}?text=${encodeURIComponent(mensaje)}`, "_blank", "noopener,noreferrer");
  };

  return (
    <section className="sec sec-sand" id="contacto">
      <div className="container contact-grid">
        <div>
          <Eyebrow>Contacto</Eyebrow>
          <h2 className="h2 big">Hablemos de tu próximo envío.</h2>
          <p className="lead">Completá el formulario o comunicate con nuestra Casa Central en Av. 1 y Calle 47.</p>
          <div className="cbox">
            <div><small>WhatsApp · Casa Central</small><strong>11 0000-1234</strong></div>
            <div><small>Teléfonos · Casa Central</small><strong>11 0000-1234</strong></div>
            <div><small>Correo</small><strong>Siger@transporte.com.ar</strong></div>
          </div>
        </div>
        <form className="form" onSubmit={enviar} noValidate>
          <h3>Solicitá una cotización</h3>
          <p className="fsub">Contanos los datos del envío y te respondemos a la brevedad.</p>
          <div className="fgrid">
            <label>Nombre y apellido<input placeholder="Tu nombre" value={valores.nombre} onChange={set("nombre")} />{errores.nombre && <span className="err">{errores.nombre}</span>}</label>
            <label>Empresa o comercio<input placeholder="Nombre de la empresa" value={valores.empresa} onChange={set("empresa")} />{errores.empresa && <span className="err">{errores.empresa}</span>}</label>
            <label>Teléfono<input placeholder="Tu teléfono" inputMode="numeric" value={valores.telefono} onChange={set("telefono")} />{errores.telefono && <span className="err">{errores.telefono}</span>}</label>
            <label>Origen del envío<input placeholder="Localidad de origen" value={valores.origen} onChange={set("origen")} />{errores.origen && <span className="err">{errores.origen}</span>}</label>
            <label className="full">Destino<input placeholder="Localidad de destino" value={valores.destino} onChange={set("destino")} />{errores.destino && <span className="err">{errores.destino}</span>}</label>
            <label className="full">Detalle de la carga<textarea rows={5} placeholder="Contanos qué necesitás enviar" value={valores.detalle} onChange={set("detalle")} />{errores.detalle && <span className="err">{errores.detalle}</span>}</label>
          </div>
          <button type="submit" className="btn btn-primary" style={{ marginTop: 22 }}>Enviar consulta</button>
        </form>
      </div>
    </section>
  );
}

export function Footer({ compact = false }: { compact?: boolean }) {
  return (
    <footer className="footer">
      <div className="container foot-in">
        <div><strong>SIGER</strong><p>Encomiendas y cargas generales</p></div>
        {!compact && <nav>{[...nav, { t: "Contacto", href: "#contacto" }].map((n) => <a key={n.t} href={n.href}>{n.t}</a>)}</nav>}
      </div>
    </footer>
  );
}
