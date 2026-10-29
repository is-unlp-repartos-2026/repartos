import { useEffect, useRef, useState, type FormEvent } from "react";
import { ArrowRight, Check, KeyRound, LogOut, PackagePlus, Trash2, Truck, X } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Header } from "./Header";
import { Footer } from "./Inferior";
import {
  DEMO_CHANNEL, demoLoginSchema, demoShipments, driverRegistrationSchema, generateDriverToken, shipmentSchema,
  type DemoMessage, type DriverToken, type Shipment, type ShipmentInput,
} from "@/lib/shipment-demo";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription } from "@/components/ui/dialog";

type Draft = ShipmentInput & { repartidor: string };
const emptyShipment: Draft = { origen: "", destino: "", destinatario: "", telefono: "", detalle: "", repartidor: "" };
const fieldLabels = { origen: "Origen", destino: "Destino", destinatario: "Destinatario", telefono: "Teléfono", detalle: "Detalles del pedido" } as const;

function useChannel(onMessage: (m: DemoMessage) => void) {
  const ref = useRef<BroadcastChannel | null>(null);
  const handler = useRef(onMessage);
  handler.current = onMessage;
  useEffect(() => {
    if (typeof BroadcastChannel === "undefined") return;
    const ch = new BroadcastChannel(DEMO_CHANNEL);
    ch.onmessage = (e) => handler.current(e.data as DemoMessage);
    ref.current = ch;
    return () => { ch.close(); ref.current = null; };
  }, []);
  return (m: DemoMessage) => ref.current?.postMessage(m);
}

export function StaffPortal({ role }: { role: "repartidor" | "operario" }) {
  return role === "repartidor" ? <DriverPortal /> : <OperatorPortal />;
}

function Shell({ role, title, onLogout, children }: { role: string; title: string; onLogout?: (() => void) | undefined; children: React.ReactNode }) {
  return <div className="site staff-page">
    <Header compact />
    <main className="sec sec-white staff-main"><div className="container">
      <div className="staff-heading">
        <div><p className="eyebrow">SIGER · {role}</p><h1 className="h2">{title}</h1></div>
        {onLogout && <Button variant="outline" className="staff-secondary" onClick={onLogout}><LogOut />Salir</Button>}
      </div>
      <p className="demo-notice">Demostración · Sin verificación real. Datos de ejemplo, no se guardan.</p>
      {children}
    </div></main><Footer compact />
  </div>;
}

function DriverPortal() {
  const [token, setToken] = useState<DriverToken | null>(null);
  const [pending, setPending] = useState<string | null>(null);
  const [error, setError] = useState("");
  const [state, setState] = useState<{ tokens: DriverToken[]; shipments: Shipment[] } | null>(null);
  const [pedidoSeleccionado, setPedidoSeleccionado] = useState<Shipment | null>(null);

  const post = useChannel((m) => { if (m.type === "sync") setState({ tokens: m.tokens, shipments: m.shipments }); });

  useEffect(() => {
    if (!pending) return;
    const t = state?.tokens.find((x) => x.token === pending);
    if (t) { setToken(t); setPending(null); setError(""); return; }
    const timer = setTimeout(() => { setPending(null); setError("Token inválido o dado de baja."); }, 800);
    return () => clearTimeout(timer);
  }, [pending, state]);

  useEffect(() => { if (token && state && !state.tokens.some((t) => t.token === token.token)) { setToken(null); setError("Tu token fue dado de baja."); } }, [state, token]);

  function login(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    const tVal = new FormData(e.currentTarget).get("token")?.toString().toUpperCase() ?? "";
    if (tVal.length !== 4) { setError("El token debe tener 4 caracteres."); return; }
    setError(""); setPending(tVal); post({ type: "request" });
  }

  const mine = token && state ? state.shipments.filter((s) => s.repartidor === token.token) : [];
  const miInfo = token && state ? state.tokens.find((t) => t.token === token.token): null;
  
  return (
    <Shell role="Repartidor" title={token ? `Mis entregas - ${token.nombre}` : "Acceso de repartidor"} onLogout={token ? () => setToken(null) : undefined}>
      {!token ? (
        <form className="form staff-login" onSubmit={login} noValidate>
          <h2>Ingresá tu token</h2>
          <div className="fgrid">
            <label className="full">Token de 4 caracteres
              <input name="token" maxLength={4} autoComplete="off" style={{ textTransform: "uppercase", letterSpacing: "0.3em" }} required />
            </label>
          </div>
          {error && <p className="staff-error" role="alert">{error}</p>}
          <Button className="btn btn-primary staff-submit" type="submit" disabled={!!pending}>{pending ? "Verificando…" : "Ingresar"}<ArrowRight /></Button>
        </form>
      ) : mine.length === 0 ? (
        <p className="demo-notice" style={{ marginTop: 24 }}>No tenés pedidos asignados.</p>
      ) : (
        <>
          <div style={{marginTop: 20, marginBottom: 20, padding: 16, border: "1px solid #ddd", borderRadius: 8, display: "flex", justifyContent: "space-between", alignItems: "center",}}>
          <span> Estado actual:
          <strong style={{ marginLeft: 8 }}> {miInfo?.activo ? "Activo" : "Inactivo"} </strong> </span><Button onClick={() => token && post({ type: "toggleDisponibilidad", token: token.token, }) } > {miInfo?.activo ? "Ponerse inactivo" : "Ponerse activo"} </Button> </div>
          <div style={{ display: "grid", gap: 16, marginTop: 20 }}>
            {mine.map((s) => (
              <article className="shipment-card" key={s.guia} style={{ cursor: "pointer", transition: "box-shadow 0.2s" }} onClick={() => setPedidoSeleccionado(s)}>
                <div className="shipment-card-head">
                  <h2><Truck />{s.guia}</h2>
                  <span className="staff-status" role="status">{s.estado}</span>
                </div>
                <dl className="shipment-details">
                  <div><dt>Origen</dt><dd>{s.origen}</dd></div>
                  <div><dt>Destino</dt><dd>{s.destino}</dd></div>
                </dl>
                <div style={{ marginTop: 12, display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                  <Button variant="outline" size="sm" onClick={() => setPedidoSeleccionado(s)}>Ver detalle</Button>
                  {s.estado === "Pendiente de aceptación" && (
                    <div className="staff-actions" onClick={(e) => e.stopPropagation()}>
                      <Button className="btn btn-primary" size="sm" onClick={() => post({ type: "decide", token: token.token, guia: s.guia, estado: "Aceptado" })}><Check />Aceptar</Button>
                      <Button variant="outline" size="sm" className="staff-secondary" onClick={() => post({ type: "decide", token: token.token, guia: s.guia, estado: "Rechazado" })}><X />Rechazar</Button>
                    </div>
                  )}
                </div>
              </article>
            ))}
          </div>

          <Dialog open={!!pedidoSeleccionado} onOpenChange={(open) => !open && setPedidoSeleccionado(null)}>
            <DialogContent className="sm:max-w-[500px]">
              <DialogHeader>
                <DialogTitle>Detalle del pedido {pedidoSeleccionado?.guia}</DialogTitle>
                <DialogDescription>Información de entrega y carga asignada.</DialogDescription>
              </DialogHeader>
              {pedidoSeleccionado && (
                <dl className="shipment-details" style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12, marginTop: 16 }}>
                  <div><dt>Origen</dt><dd>{pedidoSeleccionado.origen}</dd></div>
                  <div><dt>Destino</dt><dd>{pedidoSeleccionado.destino}</dd></div>
                  <div><dt>Receptor</dt><dd>{pedidoSeleccionado.destinatario}</dd></div>
                  <div><dt>Documento receptor</dt><dd>{pedidoSeleccionado.telefono}</dd></div>
                  <div><dt>Peso</dt><dd>4.5 kg</dd></div>
                  <div><dt>Dimensiones</dt><dd>35 x 25 x 20 cm</dd></div>
                </dl>
              )}
            </DialogContent>
          </Dialog>
        </>
      )}
    </Shell>
  );
}

const demoRepartidoresIniciales: DriverToken[] = [
  { token: "RP01", nombre: "Carlos Gómez", documento: "38.123.456", correo: "carlos@ejemplo.com", pesoMaxKg: 25, dimensionesMax: "60 x 40 x 40 cm", habilitado: true, activo: true },
  { token: "RP02", nombre: "Lucía Fernández", documento: "40.987.654", correo: "lucia@ejemplo.com", pesoMaxKg: 15, dimensionesMax: "40 x 30 x 30 cm", habilitado: false, activo: false },
  { token: "RP03", nombre: "Martín Benítez", documento: "35.456.789", correo: "martin@ejemplo.com", pesoMaxKg: 50, dimensionesMax: "100 x 80 x 60 cm", habilitado: true, activo: false },
];

function OperatorPortal() {
  const [loggedIn, setLoggedIn] = useState(false);
  const [error, setError] = useState("");
  const [shipments, setShipments] = useState<Shipment[]>(() => demoShipments.map((s) => ({ ...s })));
  const [tokens, setTokens] = useState<DriverToken[]>(demoRepartidoresIniciales);
  const [adding, setAdding] = useState(false);
  const [draft, setDraft] = useState<Draft>(emptyShipment);
  
  // Alta de repartidor state
  const [driverDraft, setDriverDraft] = useState({ nombre: "", documento: "", correo: "", pesoMaxKg: "", dimensionesMax: "" });
  const [tokenError, setTokenError] = useState("");
  const [tokenGenerado, setTokenGenerado] = useState("");

  const [seccion, setSeccion] = useState<"envios" | "repartidores">("envios");
  const [filtroHabilitacion, setFiltroHabilitacion] = useState<"todos" | "habilitados" | "deshabilitados">("todos");

  const live = useRef({ tokens, shipments, loggedIn });
  live.current = { tokens, shipments, loggedIn };

  const post = useChannel((m) => {
    if (!live.current.loggedIn) return;
    if (m.type === "request") post({ type: "sync", tokens: live.current.tokens, shipments: live.current.shipments });
    if (m.type === "decide") setShipments((rows) => rows.map((s) => s.guia === m.guia && s.repartidor === m.token ? { ...s, estado: m.estado } : s));
  });

  useEffect(() => {
    if (loggedIn) post({ type: "sync", tokens, shipments });
  }, [tokens, shipments, loggedIn]); // eslint-disable-line react-hooks/exhaustive-deps

  function login(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    const f = new FormData(e.currentTarget);
    const r = demoLoginSchema.safeParse({ usuario: f.get("usuario"), password: f.get("password") });
    if (!r.success) { setError(r.error.issues[0]?.message ?? "Completá tus datos."); return; }
    setError(""); e.currentTarget.reset(); setLoggedIn(true);
  }

  function logout() {
    post({ type: "sync", tokens: [], shipments: [] });
    setLoggedIn(false); setError(""); setAdding(false); setDraft(emptyShipment);
    setTokens(demoRepartidoresIniciales); setShipments(demoShipments.map((s) => ({ ...s })));
  }

  function registrarRepartidor(e: FormEvent) {
    e.preventDefault();
    setTokenGenerado("");
    const r = driverRegistrationSchema.safeParse(driverDraft);
    if (!r.success) { setTokenError(r.error.issues[0]?.message ?? "Revisá los datos ingresados."); return; }

    if (tokens.some((t) => t.documento === r.data.documento)) {
      setTokenError("El repartidor ya está registrado en el sistema.");
      return;
    }

    const nuevoToken = generateDriverToken(tokens.map((x) => x.token));
    setTokens((t) => [...t, { ...r.data, token: nuevoToken, habilitado: true, activo: false }]);
    setTokenGenerado(nuevoToken);
    setDriverDraft({ nombre: "", documento: "", correo: "", pesoMaxKg: "", dimensionesMax: "" });
    setTokenError("");
  }

  function revoke(token: string) {
    setTokens((t) => t.filter((x) => x.token !== token));
    setShipments((rows) => rows.map((s) => s.repartidor === token ? { ...s, repartidor: undefined, estado: "Pendiente de asignación" } : s));
  }

  function addShipment(e: FormEvent) {
    e.preventDefault();
    const r = shipmentSchema.safeParse(draft);
    if (!r.success) { setError(r.error.issues[0]?.message ?? "Revisá los datos."); return; }
    const repartidor = draft.repartidor || undefined;
    setShipments((rows) => [...rows, { ...r.data, guia: `DEMO-${String(rows.length + 1).padStart(3, "0")}`, repartidor, estado: repartidor ? "Pendiente de aceptación" : "Pendiente de asignación" }]);
    setAdding(false); setDraft(emptyShipment); setError("");
  }

  function assign(guia: string, token: string) {
    setShipments((rows) => rows.map((s) => s.guia === guia ? { ...s, repartidor: token || undefined, estado: token ? "Pendiente de aceptación" : "Pendiente de asignación" } : s));
  }

  const driverLabel = (t?: string) => {
    const d = tokens.find((x) => x.token === t);
    return d ? `${d.token} · ${d.nombre}` : "Sin asignar";
  };

  const repartidoresFiltrados = tokens.filter((rep) => {
    if (filtroHabilitacion === "habilitados") return rep.habilitado;
    if (filtroHabilitacion === "deshabilitados") return !rep.habilitado;
    return true;
  });

  if (!loggedIn) {
    return (
      <Shell role="Operario" title="Acceso de personal">
        <form className="form staff-login" onSubmit={login} noValidate>
          <h2>Ingresar como operario</h2>
          <div className="fgrid">
            <label className="full">Usuario<input name="usuario" autoComplete="username" maxLength={100} required /></label>
            <label className="full">Contraseña<input name="password" type="password" autoComplete="current-password" maxLength={128} required /></label>
          </div>
          {error && <p className="staff-error" role="alert">{error}</p>}
          <Button className="btn btn-primary staff-submit" type="submit">Ingresar a demostración<ArrowRight /></Button>
        </form>
      </Shell>
    );
  }

  return (
    <Shell role="Operario" title="Panel de Gestión" onLogout={logout}>
      <div style={{ display: "flex", gap: 12, marginBottom: 24 }}>
        <Button type="button" variant={seccion === "envios" ? "default" : "outline"} className={seccion === "envios" ? "btn btn-primary" : "staff-secondary"} onClick={() => setSeccion("envios")}>Envíos en proceso</Button>
        <Button type="button" variant={seccion === "repartidores" ? "default" : "outline"} className={seccion === "repartidores" ? "btn btn-primary" : "staff-secondary"} onClick={() => { setSeccion("repartidores"); setTokenGenerado(""); setTokenError(""); }}>Sección de repartidores</Button>
      </div>

      {seccion === "repartidores" ? (
        <section aria-labelledby="repartidores-heading">
          <div className="form shipment-create" style={{ padding: 24, marginBottom: 32 }}>
            <h3 style={{ marginTop: 0, marginBottom: 20, fontSize: 18 }}>Alta de nuevo repartidor</h3>
            <form className="fgrid" onSubmit={registrarRepartidor} noValidate>
              <label>Nombre<input value={driverDraft.nombre} onChange={(e) => setDriverDraft(v => ({ ...v, nombre: e.target.value }))} /></label>
              <label>Documento<input value={driverDraft.documento} onChange={(e) => setDriverDraft(v => ({ ...v, documento: e.target.value }))} /></label>
              <label>Correo electrónico<input type="email" value={driverDraft.correo} onChange={(e) => setDriverDraft(v => ({ ...v, correo: e.target.value }))} /></label>
              <label>Peso máximo (kg)<input type="number" value={driverDraft.pesoMaxKg} onChange={(e) => setDriverDraft(v => ({ ...v, pesoMaxKg: e.target.value }))} /></label>
              <label className="full">Dimensiones máximas<input value={driverDraft.dimensionesMax} placeholder="Ej: 60 x 40 x 40 cm" onChange={(e) => setDriverDraft(v => ({ ...v, dimensionesMax: e.target.value }))} /></label>
              {tokenError && <p className="staff-error full" role="alert">{tokenError}</p>}
              <div className="full" style={{ marginTop: 12 }}>
                <Button type="submit" className="btn btn-primary"><KeyRound />Registrar y habilitar acceso</Button>
              </div>
            </form>
            {tokenGenerado && (
              <div className="demo-notice" style={{ marginTop: 24, borderLeftColor: "var(--m-red)", backgroundColor: "#fef2f2" }}>
                <strong>¡Alta exitosa!</strong> Entregale este código de acceso al repartidor: <strong style={{ fontSize: 20, letterSpacing: "0.15em", marginLeft: 8 }}>{tokenGenerado}</strong>
              </div>
            )}
          </div>

          <div className="staff-toolbar" style={{ flexWrap: "wrap", gap: 16 }}>
            <div>
              <h2 id="repartidores-heading" style={{ margin: 0, fontSize: 20 }}>Listado de repartidores</h2>
              <p style={{ margin: 0, color: "var(--muted-foreground, #666)" }}>Mostrando {repartidoresFiltrados.length} repartidores</p>
            </div>
            <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
              <label htmlFor="filtro-hab" style={{ fontSize: 14, fontWeight: 500 }}>Filtrar por habilitación:</label>
              <select id="filtro-hab" value={filtroHabilitacion} onChange={(e) => setFiltroHabilitacion(e.target.value as "todos" | "habilitados" | "deshabilitados")} style={{ padding: "6px 12px", borderRadius: 6, border: "1px solid #ccc" }}>
                <option value="todos">Todos</option>
                <option value="habilitados">Habilitados</option>
                <option value="deshabilitados">Deshabilitados</option>
              </select>
            </div>
          </div>

          <div className="shipment-table-wrap" style={{ marginTop: 16 }}>
            <table className="shipment-table">
              <caption>Nómina de repartidores</caption>
              <thead>
                <tr>
                  <th scope="col">Nombre</th><th scope="col">Documento</th><th scope="col">Carga habilitada</th><th scope="col">Habilitación</th><th scope="col">Disponibilidad</th><th scope="col">Acciones</th>
                </tr>
              </thead>
              <tbody>
                {repartidoresFiltrados.length === 0 ? (
                  <tr><td colSpan={6} style={{ textAlign: "center", padding: 24 }}>No se encontraron repartidores para el filtro seleccionado.</td></tr>
                ) : (
                  repartidoresFiltrados.map((rep) => (
                    <tr key={rep.token}>
                      <th scope="row">
                        <strong style={{ display: "block" }}>{rep.nombre}</strong>
                        <small style={{ color: "var(--m-muted)", letterSpacing: "0.1em" }}>{rep.token}</small>
                      </th>
                      <td>{rep.documento}</td>
                      <td>{rep.pesoMaxKg} kg — {rep.dimensionesMax}</td>
                      <td><span className="staff-status" style={{ background: rep.habilitado ? "#e6f4ea" : "#fce8e6", color: rep.habilitado ? "#137333" : "#c5221f" }}>{rep.habilitado ? "Habilitado" : "Deshabilitado"}</span></td>
                      <td><span className="staff-status" style={{ background: rep.activo ? "#e8f0fe" : "#f1f3f4", color: rep.activo ? "#1a73e8" : "#5f6368" }}>{rep.activo ? "Activo" : "Inactivo"}</span></td>
                      <td><Button variant="outline" size="sm" className="staff-secondary" onClick={() => revoke(rep.token)}><Trash2 />Dar de baja</Button></td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </section>
      ) : (
        <>
          <div className="staff-toolbar">
            <p>{shipments.length} envíos</p>
            <Button className="btn btn-primary" onClick={() => { setAdding(true); setError(""); }}><PackagePlus />Subir envío</Button>
          </div>

          {adding && (
            <form className="form shipment-create" onSubmit={addShipment} noValidate>
              <div className="shipment-card-head">
                <h2>Nuevo envío</h2>
                <Button type="button" variant="ghost" size="icon" aria-label="Cerrar nuevo envío" onClick={() => { setAdding(false); setError(""); }}><X /></Button>
              </div>
              <div className="fgrid">
                {(["origen", "destino", "destinatario", "telefono", "detalle"] as const).map((field) => (
                  <label className={field === "detalle" ? "full" : ""} key={field}>
                    {fieldLabels[field]}
                    {field === "detalle"
                      ? <textarea rows={3} maxLength={1000} value={draft[field]} onChange={(e) => setDraft((v) => ({ ...v, [field]: e.target.value }))} />
                      : <input maxLength={field === "telefono" ? 20 : 200} inputMode={field === "telefono" ? "numeric" : "text"} value={draft[field]} onChange={(e) => setDraft((v) => ({ ...v, [field]: e.target.value }))} />}
                  </label>
                ))}
                <label className="full">Repartidor
                  <select value={draft.repartidor} onChange={(e) => setDraft((v) => ({ ...v, repartidor: e.target.value }))}>
                    <option value="">Sin asignar</option>
                    {tokens.map((t) => <option key={t.token} value={t.token}>{t.token} · {t.nombre}</option>)}
                  </select>
                </label>
              </div>
              {error && <p className="staff-error" role="alert">{error}</p>}
              <Button type="submit" className="btn btn-primary staff-submit"><Check />Guardar envío de ejemplo</Button>
            </form>
          )}

          <div className="shipment-table-wrap">
            <table className="shipment-table">
              <caption>Registro de envíos · Demostración</caption>
              <thead>
                <tr>{["Guía", "Origen", "Destino", "Destinatario", "Teléfono", "Detalles del pedido", "Repartidor", "Estado"].map((n) => <th key={n} scope="col">{n}</th>)}</tr>
              </thead>
              <tbody>
                {shipments.map((s) => (
                  <tr key={s.guia}>
                    <th scope="row">{s.guia}</th><td>{s.origen}</td><td>{s.destino}</td><td>{s.destinatario}</td><td>{s.telefono}</td><td>{s.detalle}</td>
                    <td>
                      <select aria-label={`Repartidor de ${s.guia}`} value={tokens.some((t) => t.token === s.repartidor) ? s.repartidor : ""} onChange={(e) => assign(s.guia, e.target.value)}>
                        <option value="">Sin asignar</option>
                        {tokens.map((t) => <option key={t.token} value={t.token}>{driverLabel(t.token)}</option>)}
                      </select>
                    </td>
                    <td><span className="staff-status">{s.estado}</span></td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </>
      )}
    </Shell>
  );
}
