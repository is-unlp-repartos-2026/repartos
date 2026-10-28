import { useEffect, useRef, useState, type FormEvent } from "react";
import { ArrowRight, Check, KeyRound, LogOut, PackagePlus, Trash2, Truck, X } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Header } from "./Header";
import { Footer } from "./Inferior";
import {
  DEMO_CHANNEL, demoLoginSchema, demoShipments, driverNameSchema, driverTokenSchema, generateDriverToken, shipmentSchema,
  type DemoMessage, type DriverToken, type Shipment, type ShipmentInput,
} from "@/lib/shipment-demo";

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
  const post = useChannel((m) => { if (m.type === "sync") setState({ tokens: m.tokens, shipments: m.shipments }); });

  useEffect(() => {
    if (!pending) return;
    const t = state?.tokens.find((x) => x.token === pending);
    if (t) { setToken(t); setPending(null); setError(""); return; }
    const timer = setTimeout(() => { setPending(null); setError("Token inválido o dado de baja. Pedile uno al operario (con su página abierta)."); }, 800);
    return () => clearTimeout(timer);
  }, [pending, state]);

  useEffect(() => { if (token && state && !state.tokens.some((t) => t.token === token.token)) { setToken(null); setError("Tu token fue dado de baja."); } }, [state, token]);

  function login(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    const r = driverTokenSchema.safeParse(new FormData(e.currentTarget).get("token") ?? "");
    if (!r.success) { setError(r.error.issues[0]?.message ?? "Token inválido."); return; }
    setError(""); setPending(r.data); post({ type: "request" });
  }

  const mine = token && state ? state.shipments.filter((s) => s.repartidor === token.token) : [];
  return <Shell role="Repartidor" title={token ? `Hola, ${token.nombre}` : "Acceso de repartidor"} onLogout={token ? () => setToken(null) : undefined}>
    {!token ? <form className="form staff-login" onSubmit={login} noValidate>
      <h2>Ingresá tu token</h2>
      <div className="fgrid"><label className="full">Token de 4 caracteres<input name="token" maxLength={4} autoComplete="off" style={{ textTransform: "uppercase", letterSpacing: "0.3em" }} required /></label></div>
      {error && <p className="staff-error" role="alert">{error}</p>}
      <Button className="btn btn-primary staff-submit" type="submit" disabled={!!pending}>{pending ? "Verificando…" : "Ingresar"}<ArrowRight /></Button>
    </form> : mine.length === 0 ? <p>No tenés envíos asignados por ahora.</p> : mine.map((s) => <article className="shipment-card" key={s.guia} style={{ marginBottom: 20 }}>
      <div className="shipment-card-head"><h2><Truck />{s.guia}</h2><span className="staff-status" role="status">{s.estado}</span></div>
      <dl className="shipment-details">
        <div><dt>Origen</dt><dd>{s.origen}</dd></div>
        <div><dt>Destino</dt><dd>{s.destino}</dd></div>
        <div><dt>Destinatario</dt><dd>{s.destinatario}</dd></div>
        <div><dt>Teléfono</dt><dd>{s.telefono}</dd></div>
        <div className="detail-full"><dt>Detalles del pedido</dt><dd>{s.detalle}</dd></div>
      </dl>
      {s.estado === "Pendiente de aceptación" && <div className="staff-actions">
        <Button className="btn btn-primary" onClick={() => post({ type: "decide", token: token.token, guia: s.guia, estado: "Aceptado" })}><Check />Aceptar pedido</Button>
        <Button variant="outline" className="staff-secondary" onClick={() => post({ type: "decide", token: token.token, guia: s.guia, estado: "Rechazado" })}><X />Rechazar pedido</Button>
      </div>}
    </article>)}
  </Shell>;
}

function OperatorPortal() {
  const [loggedIn, setLoggedIn] = useState(false);
  const [error, setError] = useState("");
  const [shipments, setShipments] = useState<Shipment[]>(() => demoShipments.map((s) => ({ ...s })));
  const [tokens, setTokens] = useState<DriverToken[]>([]);
  const [adding, setAdding] = useState(false);
  const [draft, setDraft] = useState<Draft>(emptyShipment);
  const [driverName, setDriverName] = useState("");
  const [tokenError, setTokenError] = useState("");
  const live = useRef({ tokens, shipments, loggedIn });
  live.current = { tokens, shipments, loggedIn };

  const post = useChannel((m) => {
    if (!live.current.loggedIn) return;
    if (m.type === "request") post({ type: "sync", tokens: live.current.tokens, shipments: live.current.shipments });
    if (m.type === "decide") setShipments((rows) => rows.map((s) => s.guia === m.guia && s.repartidor === m.token ? { ...s, estado: m.estado } : s));
  });
  useEffect(() => { if (loggedIn) post({ type: "sync", tokens, shipments }); }, [tokens, shipments, loggedIn]); // eslint-disable-line react-hooks/exhaustive-deps

  function login(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    const f = new FormData(e.currentTarget);
    const r = demoLoginSchema.safeParse({ usuario: f.get("usuario"), password: f.get("password") });
    if (!r.success) { setError(r.error.issues[0]?.message ?? "Completá tus datos."); return; }
    setError(""); e.currentTarget.reset(); setLoggedIn(true);
  }
  function logout() {
    post({ type: "sync", tokens: [], shipments: [] });
    setLoggedIn(false); setError(""); setAdding(false); setDraft(emptyShipment); setTokens([]);
    setShipments(demoShipments.map((s) => ({ ...s })));
  }
  function createToken(e: FormEvent) {
    e.preventDefault();
    const r = driverNameSchema.safeParse(driverName);
    if (!r.success) { setTokenError(r.error.issues[0]?.message ?? ""); return; }
    setTokens((t) => [...t, { token: generateDriverToken(t.map((x) => x.token)), nombre: r.data }]);
    setDriverName(""); setTokenError("");
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
  const driverLabel = (t?: string) => { const d = tokens.find((x) => x.token === t); return d ? `${d.token} · ${d.nombre}` : "Sin asignar"; };

  if (!loggedIn) return <Shell role="Operario" title="Acceso de personal">
    <form className="form staff-login" onSubmit={login} noValidate>
      <h2>Ingresar como operario</h2>
      <div className="fgrid">
        <label className="full">Usuario<input name="usuario" autoComplete="username" maxLength={100} required /></label>
        <label className="full">Contraseña<input name="password" type="password" autoComplete="current-password" maxLength={128} required /></label>
      </div>
      {error && <p className="staff-error" role="alert">{error}</p>}
      <Button className="btn btn-primary staff-submit" type="submit">Ingresar a demostración<ArrowRight /></Button>
    </form>
  </Shell>;

  return <Shell role="Operario" title="Envíos en proceso" onLogout={logout}>
    <section className="form shipment-create" aria-labelledby="tokens-title">
      <h2 id="tokens-title">Tokens de repartidores</h2>
      <form className="fgrid" onSubmit={createToken} noValidate>
        <label className="full">Nombre del repartidor<input value={driverName} maxLength={100} onChange={(e) => setDriverName(e.target.value)} /></label>
        {tokenError && <p className="staff-error" role="alert">{tokenError}</p>}
        <Button type="submit" className="btn btn-primary"><KeyRound />Generar Token Repartidor</Button>
      </form>
      {tokens.length > 0 && <ul style={{ listStyle: "none", padding: 0, marginTop: 16, display: "grid", gap: 8 }}>
        {tokens.map((t) => <li key={t.token} style={{ display: "flex", alignItems: "center", gap: 12, flexWrap: "wrap" }}>
          <strong style={{ letterSpacing: "0.2em", fontSize: 18 }}>{t.token}</strong><span>{t.nombre}</span>
          <Button variant="outline" size="sm" className="staff-secondary" onClick={() => revoke(t.token)}><Trash2 />Dar de baja</Button>
        </li>)}
      </ul>}
    </section>

    <div className="staff-toolbar"><p>{shipments.length} envíos</p><Button className="btn btn-primary" onClick={() => { setAdding(true); setError(""); }}><PackagePlus />Subir envío</Button></div>
    {adding && <form className="form shipment-create" onSubmit={addShipment} noValidate>
      <div className="shipment-card-head"><h2>Nuevo envío</h2><Button type="button" variant="ghost" size="icon" aria-label="Cerrar nuevo envío" onClick={() => { setAdding(false); setError(""); }}><X /></Button></div>
      <div className="fgrid">
        {(["origen", "destino", "destinatario", "telefono", "detalle"] as const).map((field) => <label className={field === "detalle" ? "full" : ""} key={field}>{fieldLabels[field]}
          {field === "detalle"
            ? <textarea rows={3} maxLength={1000} value={draft[field]} onChange={(e) => setDraft((v) => ({ ...v, [field]: e.target.value }))} />
            : <input maxLength={field === "telefono" ? 20 : 200} inputMode={field === "telefono" ? "numeric" : "text"} value={draft[field]} onChange={(e) => setDraft((v) => ({ ...v, [field]: e.target.value }))} />}
        </label>)}
        <label className="full">Repartidor<select value={draft.repartidor} onChange={(e) => setDraft((v) => ({ ...v, repartidor: e.target.value }))}>
          <option value="">Sin asignar</option>{tokens.map((t) => <option key={t.token} value={t.token}>{t.token} · {t.nombre}</option>)}
        </select></label>
      </div>
      {error && <p className="staff-error" role="alert">{error}</p>}
      <Button type="submit" className="btn btn-primary staff-submit"><Check />Guardar envío de ejemplo</Button>
    </form>}
    <div className="shipment-table-wrap"><table className="shipment-table">
      <caption>Registro de envíos · Demostración</caption>
      <thead><tr>{["Guía", "Origen", "Destino", "Destinatario", "Teléfono", "Detalles del pedido", "Repartidor", "Estado"].map((n) => <th key={n} scope="col">{n}</th>)}</tr></thead>
      <tbody>{shipments.map((s) => <tr key={s.guia}>
        <th scope="row">{s.guia}</th><td>{s.origen}</td><td>{s.destino}</td><td>{s.destinatario}</td><td>{s.telefono}</td><td>{s.detalle}</td>
        <td><select aria-label={`Repartidor de ${s.guia}`} value={tokens.some((t) => t.token === s.repartidor) ? s.repartidor : ""} onChange={(e) => assign(s.guia, e.target.value)}>
          <option value="">Sin asignar</option>{tokens.map((t) => <option key={t.token} value={t.token}>{driverLabel(t.token)}</option>)}
        </select></td>
        <td><span className="staff-status">{s.estado}</span></td>
      </tr>)}</tbody>
    </table></div>
  </Shell>;
}
