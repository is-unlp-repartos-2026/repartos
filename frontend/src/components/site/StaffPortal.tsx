import { useState, type FormEvent } from "react";
import { ArrowRight, Check, LogOut, PackagePlus, Truck, X } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Header } from "./Header";
import { Footer } from "./Inferior";
import { demoLoginSchema, demoShipments, shipmentSchema, type Shipment, type ShipmentInput } from "@/lib/shipment-demo";

const emptyShipment: ShipmentInput = { origen: "", destino: "", destinatario: "", telefono: "", detalle: "" };

export function StaffPortal({ role }: { role: "repartidor" | "operario" }) {
  const [loggedIn, setLoggedIn] = useState(false);
  const [error, setError] = useState("");
  const [shipments, setShipments] = useState<Shipment[]>(() => demoShipments.map((s) => ({ ...s })));
  const [adding, setAdding] = useState(false);
  const [draft, setDraft] = useState<ShipmentInput>(emptyShipment);
  const isDriver = role === "repartidor";
  const assigned = shipments[0];

  function login(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    const result = demoLoginSchema.safeParse({ usuario: form.get("usuario"), password: form.get("password") });
    if (!result.success) { setError(result.error.issues[0]?.message ?? "Completá tus datos."); return; }
    setError("");
    event.currentTarget.reset();
    setLoggedIn(true);
  }

  function addShipment(event: FormEvent) {
    event.preventDefault();
    const result = shipmentSchema.safeParse(draft);
    if (!result.success) { setError(result.error.issues[0]?.message ?? "Revisá los datos."); return; }
    setShipments((rows) => [...rows, { ...result.data, guia: `DEMO-${String(rows.length + 1).padStart(3, "0")}`, estado: "Pendiente de asignación" }]);
    setAdding(false); setDraft(emptyShipment); setError("");
  }

  function decide(estado: string) {
    setShipments((rows) => rows.map((s, index) => index === 0 ? { ...s, estado } : s));
  }

  return <div className="site staff-page">
    <Header compact />
    <main className="sec sec-white staff-main">
      <div className="container">
        <div className="staff-heading">
          <div><p className="eyebrow">SIGER · {isDriver ? "Repartidor" : "Operario"}</p><h1 className="h2">{loggedIn ? (isDriver ? "Mi envío asignado" : "Envíos en proceso") : "Acceso de personal"}</h1></div>
          {loggedIn && <Button variant="outline" className="staff-secondary" onClick={() => { setLoggedIn(false); setError(""); setAdding(false); setDraft(emptyShipment); setShipments(demoShipments.map((s) => ({ ...s }))); }}><LogOut />Salir</Button>}
        </div>
        <p className="demo-notice">Demostración · Sin verificación de usuarios. Datos de ejemplo, no se guardan.</p>
        {!loggedIn ? <form className="form staff-login" onSubmit={login} noValidate>
          <h2>Ingresar como {role}</h2>
          <div className="fgrid">
            <label className="full">Usuario<input name="usuario" autoComplete="username" maxLength={100} required /></label>
            <label className="full">Contraseña<input name="password" type="password" autoComplete="current-password" maxLength={128} required /></label>
          </div>
          {error && <p className="staff-error" role="alert">{error}</p>}
          <Button className="btn btn-primary staff-submit" type="submit">Ingresar a demostración<ArrowRight /></Button>
        </form> : isDriver && assigned ? <article className="shipment-card">
          <div className="shipment-card-head"><h2><Truck />{assigned.guia}</h2><span className="staff-status" role="status">{assigned.estado}</span></div>
          <dl className="shipment-details">
            <div><dt>Origen</dt><dd>{assigned.origen}</dd></div>
            <div><dt>Destino</dt><dd>{assigned.destino}</dd></div>
            <div><dt>Destinatario</dt><dd>{assigned.destinatario}</dd></div>
            <div><dt>Teléfono</dt><dd>{assigned.telefono}</dd></div>
            <div className="detail-full"><dt>Detalles del pedido</dt><dd>{assigned.detalle}</dd></div>
          </dl>
          {assigned.estado === "Pendiente de aceptación" && <div className="staff-actions"><Button className="btn btn-primary" onClick={() => decide("Aceptado")}><Check />Aceptar pedido</Button><Button variant="outline" className="staff-secondary" onClick={() => decide("Rechazado")}><X />Rechazar pedido</Button></div>}
        </article> : <>
          <div className="staff-toolbar"><p>{shipments.length} envíos</p><Button className="btn btn-primary" onClick={() => { setAdding(true); setError(""); }}><PackagePlus />Subir envío</Button></div>
          {adding && <form className="form shipment-create" onSubmit={addShipment} noValidate>
            <div className="shipment-card-head"><h2>Nuevo envío</h2><Button type="button" variant="ghost" size="icon" aria-label="Cerrar nuevo envío" title="Cerrar" onClick={() => { setAdding(false); setError(""); }}><X /></Button></div>
            <div className="fgrid">{(["origen", "destino", "destinatario", "telefono", "detalle"] as const).map((field) => <label className={field === "detalle" ? "full" : ""} key={field}>{({ origen: "Origen", destino: "Destino", destinatario: "Destinatario", telefono: "Teléfono", detalle: "Detalles del pedido" })[field]}{field === "detalle" ? <textarea required rows={3} maxLength={1000} value={draft[field]} onChange={(e) => setDraft((v) => ({ ...v, [field]: e.target.value }))} /> : <input required maxLength={field === "telefono" ? 20 : 200} inputMode={field === "telefono" ? "numeric" : "text"} value={draft[field]} onChange={(e) => setDraft((v) => ({ ...v, [field]: e.target.value }))} />}</label>)}</div>
            {error && <p className="staff-error" role="alert">{error}</p>}
            <Button type="submit" className="btn btn-primary staff-submit"><Check />Guardar envío de ejemplo</Button>
          </form>}
          <div className="shipment-table-wrap"><table className="shipment-table"><caption>Registro de envíos · Demostración</caption><thead><tr>{["Guía", "Origen", "Destino", "Destinatario", "Teléfono", "Detalles del pedido", "Estado"].map((name) => <th key={name} scope="col">{name}</th>)}</tr></thead><tbody>{shipments.map((s) => <tr key={s.guia}><th scope="row">{s.guia}</th><td>{s.origen}</td><td>{s.destino}</td><td>{s.destinatario}</td><td>{s.telefono}</td><td>{s.detalle}</td><td><span className="staff-status">{s.estado}</span></td></tr>)}</tbody></table></div>
        </>}
      </div>
    </main><Footer compact />
  </div>;
}