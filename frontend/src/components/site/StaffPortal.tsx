import { useEffect, useRef, useState, type FormEvent } from "react";
import {
  ApiError, getSesionOperario, getSesionRepartidor, listarRepartidores, loginOperario, loginRepartidor, registrarRepartidor as registrarRepartidorApi,
  tokenOperario, tokenRepartidor, type Repartidor,
} from "@/lib/api";
import { ArrowRight, Check, KeyRound, LogOut, PackagePlus, Truck, X } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Header } from "./Header";
import { Footer } from "./Inferior";
import {
  DEMO_CHANNEL, demoLoginSchema, demoShipments, driverRegistrationSchema, generateDriverToken, generateTrackingCode, shipmentSchema,
  type DemoMessage, type DriverToken, type Shipment, type ShipmentInput,
} from "@/lib/shipment-demo";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription } from "@/components/ui/dialog";



type Draft = ShipmentInput;
const emptyShipment: Draft = { origen: "", destino: "", destinatario: "", documentoReceptor: "", pesoKg: 0, dimensiones: "" };
const fieldLabels = { origen: "Origen", destino: "Destino", destinatario: "Destinatario", documentoReceptor: "Documento del receptor", pesoKg: "Peso (kg)", dimensiones: "Dimensiones (Ej: 30x20x10 cm)" } as const;

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
  // Reemplazamos el token simulado por el perfil real del backend
  const [repartidor, setRepartidor] = useState<Repartidor | null>(null);
  const [pending, setPending] = useState(false);
  const [error, setError] = useState("");
  
  // Mantenemos el estado de pedidos temporalmente (aunque quedará vacío hasta integrar la API de pedidos)
  const [state, setState] = useState<{ shipments: Shipment[] } | null>(null);
  const [pedidoSeleccionado, setPedidoSeleccionado] = useState<Shipment | null>(null);
  const [avisoFinJornada, setAvisoFinJornada] = useState("");

  const post = useChannel((m) => { if (m.type === "sync") setState({ shipments: m.shipments }); });

  // HU-34: Cargar sesión guardada al abrir la aplicación
  useEffect(() => {
    const tokenGuardado = tokenRepartidor.leer();
    if (tokenGuardado) {
      setPending(true);
      getSesionRepartidor(tokenGuardado)
        .then((perfil) => setRepartidor(perfil))
        .catch((err: Error) => {
          tokenRepartidor.borrar();
          setError(err.message);
        })
        .finally(() => setPending(false));
    }
  }, []);

  async function login(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    const codigo = new FormData(e.currentTarget).get("token")?.toString().toUpperCase() ?? "";
    if (codigo.length !== 4) { setError("El código debe tener 4 caracteres."); return; }
    
    setPending(true);
    setError("");
    
    try {
      const resLogin = await loginRepartidor(codigo);
      tokenRepartidor.guardar(resLogin.token); // Guardamos la sesión en el dispositivo

      const perfil = await getSesionRepartidor(resLogin.token); // Buscamos los datos de ese token
      setRepartidor(perfil);
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setPending(false);
    }
  }

  function logout() {
    tokenRepartidor.borrar();
    setRepartidor(null);
  }

  // Al usar el backend real, el ID será un número entero. 
  // Las guías de prueba usan "RP01", por lo que esta lista se verá vacía hasta que se conecte el backend de envíos.
  const mine = repartidor && state ? state.shipments.filter((s) => s.repartidor === repartidor.id?.toString()) : [];
  
  function handleToggleDisponibilidad() {
    alert("Para cambiar la disponibilidad hay que integrar HU-13 (Comenzar jornada) y HU-14 (Terminar jornada).");
  }
  
  return (
    <Shell role="Repartidor" title={repartidor ? `Mis entregas - ${repartidor.nombre}` : "Acceso de repartidor"} onLogout={repartidor ? logout : undefined}>
      {!repartidor ? (
        <form className="form staff-login" onSubmit={login} noValidate>
          <h2>Ingresá tu código</h2>
          <div className="fgrid">
            <label className="full">Código de acceso (4 caracteres)
              <input name="token" maxLength={4} autoComplete="off" style={{ textTransform: "uppercase", letterSpacing: "0.3em" }} required />
            </label>
          </div>
          {error && <p className="staff-error" role="alert">{error}</p>}
          <Button className="btn btn-primary staff-submit" type="submit" disabled={pending}>{pending ? "Verificando…" : "Ingresar"}<ArrowRight /></Button>
        </form>
      ) : (
        <>
          <div style={{marginTop: 20, marginBottom: avisoFinJornada ? 0 : 20, padding: 16, border: "1px solid #ddd", borderRadius: 8, display: "flex", justifyContent: "space-between", alignItems: "center",}}>
            <span> Estado actual: <strong style={{ marginLeft: 8 }}> {repartidor.activo ? "Activo" : "Inactivo"} </strong> </span>
            <Button onClick={handleToggleDisponibilidad} > 
              {repartidor.activo ? "Finalizar jornada laboral" : "Comenzar jornada laboral"} 
            </Button> 
          </div>
          
          {avisoFinJornada && (
            <p className="staff-error" style={{ marginBottom: 20, marginTop: 8 }} role="alert">{avisoFinJornada}</p>
          )}

          {mine.length === 0 && ( <p className="demo-notice" style={{ marginTop: 24 }}>No tenés pedidos asignados. (Pendiente conectar con backend de envíos).</p>)}
          
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
                </div>
              </article>
            ))}
          </div>
        </>
      )}
    </Shell>
  );
}

const demoRepartidoresIniciales: DriverToken[] = [
  { token: "RP01", nombre: "Carlos Gómez", documento: "38.123.456", correo: "carlos@ejemplo.com", pesoMaxKg: 25, dimensionesMax: "60 x 40 x 40 cm", habilitado: true, activo: true },
  { token: "RP02", nombre: "Lucía Fernández", documento: "40.987.654", correo: "lucia@ejemplo.com", pesoMaxKg: 15, dimensionesMax: "40 x 30 x 30 cm", habilitado: false, activo: false },
  { token: "RP03", nombre: "Martín Benítez", documento: "35.456.789", correo: "martin@ejemplo.com", pesoMaxKg: 50, dimensionesMax: "100 x 80 x 60 cm", habilitado: true, activo: true },
];

const medidasRepartidor = [
  ["peso_max_kg", "Peso máx (kg)"], ["alto_max_cm", "Alto máx (cm)"], ["ancho_max_cm", "Ancho máx (cm)"], ["largo_max_cm", "Largo máx (cm)"],
] as const;

type BorradorRepartidor = { nombre: string; dni: string; correo: string; peso_max_kg: string; alto_max_cm: string; ancho_max_cm: string; largo_max_cm: string };
const repartidorVacio: BorradorRepartidor = { nombre: "", dni: "", correo: "", peso_max_kg: "", alto_max_cm: "", ancho_max_cm: "", largo_max_cm: "" };

// Las mismas reglas que el backend, para mostrar el error en castellano antes de enviar.
function validarRepartidor(d: BorradorRepartidor): string | null {
  if (!d.nombre.trim()) return "Completá el nombre.";
  if (!/^\d{7,8}$/.test(d.dni)) return "El DNI tiene que tener 7 u 8 números, sin puntos.";
  if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(d.correo.trim())) return "Ingresá un correo válido.";
  for (const [campo, etiqueta] of medidasRepartidor) {
    if (!(Number(d[campo]) > 0)) return `${etiqueta}: tiene que ser un número mayor a 0.`;
  }
  return null;
}

function OperatorPortal() {
  const [loggedIn, setLoggedIn] = useState(false);
  const [verificandoSesion, setVerificandoSesion] = useState(true);
  const [error, setError] = useState("");
  const [shipments, setShipments] = useState<Shipment[]>(() => demoShipments.map((s) => ({ ...s })));
  const [tokens, setTokens] = useState<DriverToken[]>(demoRepartidoresIniciales);
  const [adding, setAdding] = useState(false);
  const [draft, setDraft] = useState<Draft>(emptyShipment);
  
  const [driverDraft, setDriverDraft] = useState<BorradorRepartidor>(repartidorVacio);
  const [tokenError, setTokenError] = useState("");
  const [tokenGenerado, setTokenGenerado] = useState<{ nombre: string; codigo: string } | null>(null);
  const [registrando, setRegistrando] = useState(false);
  const [repartidores, setRepartidores] = useState<Repartidor[]>([]);
  const [errorListado, setErrorListado] = useState("");
  
  const [resultadoAltaEnvio, setResultadoAltaEnvio] = useState<{ guia: string, estado: string, aviso?: string } | null>(null);

  const [seccion, setSeccion] = useState<"envios" | "repartidores">("envios");
  const [filtroHabilitacion, setFiltroHabilitacion] = useState<"todos" | "habilitados" | "deshabilitados">("todos");

  const live = useRef({ tokens, shipments, loggedIn });
  live.current = { tokens, shipments, loggedIn };

  const post = useChannel((m) => { 
    if (!live.current.loggedIn) return;
    if (m.type === "request") post({ type: "sync", tokens: live.current.tokens, shipments: live.current.shipments });
    
    if (m.type === "toggleDisponibilidad") {
      setTokens((rows) => {
        const updatedTokens = rows.map((t) => t.token === m.token ? { ...t, activo: !t.activo } : t);
        const rep = updatedTokens.find(t => t.token === m.token);
        
        if (rep) {
          if (rep.activo) {
            setShipments(currentShipments => {
              let hasChanges = false;
              const newShipments = currentShipments.map(s => {
                if (s.estado === "Registrado" && !s.repartidor && rep.pesoMaxKg >= s.pesoKg) {
                  hasChanges = true;
                  return { ...s, repartidor: rep.token, estado: "Repartidor asignado" };
                }
                return s;
              });
              return hasChanges ? newShipments : currentShipments;
            });
          } else {
            setShipments(currentShipments => {
              let hasChanges = false;
              const newShipments = currentShipments.map(s => {
                if (s.repartidor === rep.token && s.estado === "Repartidor asignado") {
                  hasChanges = true;
                  const aptos = updatedTokens.filter(t => t.habilitado && t.activo && t.pesoMaxKg >= s.pesoKg);
                  
                  if (aptos.length > 0) {
                    return { ...s, repartidor: aptos[0]!.token, estado: "Repartidor asignado" };
                  } else {
                    return { ...s, repartidor: undefined, estado: "Registrado" };
                  }
                }
                return s;
              });
              return hasChanges ? newShipments : currentShipments;
            });
          }
        }
        return updatedTokens;
      });
    }
    
    // HU 46: Atajar la nueva propiedad fechaRetiro y volcarla al estado de la demo
    if (m.type === "decide") {
      setShipments((rows) => rows.map((s) => s.guia === m.guia && s.repartidor === m.token 
        ? { ...s, estado: m.estado, ...(m.fechaRetiro ? { fechaRetiro: m.fechaRetiro } : {}) } 
        : s));
    }
  });

  useEffect(() => {
    if (loggedIn) post({ type: "sync", tokens, shipments });
  }, [tokens, shipments, loggedIn]); // eslint-disable-line react-hooks/exhaustive-deps

  // Al abrir o recargar la página: si hay un token guardado y sigue valiendo, entra directo.
  useEffect(() => {
    const tokenGuardado = tokenOperario.leer();
    if (!tokenGuardado) { setVerificandoSesion(false); return; }
    getSesionOperario(tokenGuardado)
      .then(() => setLoggedIn(true))
      .catch(() => tokenOperario.borrar()) // venció (30 min) o no es válido: vuelve al ingreso
      .finally(() => setVerificandoSesion(false));
  }, []);

async function login(e: FormEvent<HTMLFormElement>) {
  e.preventDefault();
  const form = e.currentTarget;
  const f = new FormData(form);

  try {
    const response = await loginOperario(String(f.get("usuario")), String(f.get("password")));
    tokenOperario.guardar(response.token);
    setError("");
    form.reset();
    setLoggedIn(true);
  } catch (err) {
    setError(
      err instanceof ApiError && err.status === 401
        ? "Usuario o contraseña incorrectos."
        : "No se pudo conectar con el servidor. Intentá de nuevo."
    );
  }
}

  // Si el backend responde 401 (sesión vencida), se vuelve al ingreso con un aviso.
  function manejarErrorDeSesion(err: unknown): string {
    if (err instanceof ApiError && err.status === 401) {
      logout();
      setError("Tu sesión venció. Ingresá de nuevo.");
    }
    return (err as Error).message;
  }

  async function cargarRepartidores() {
    const token = tokenOperario.leer();
    if (!token) return;
    try {
      setRepartidores(await listarRepartidores(token));
      setErrorListado("");
    } catch (err) {
      setErrorListado(manejarErrorDeSesion(err));
    }
  }

  useEffect(() => {
    if (loggedIn && seccion === "repartidores") cargarRepartidores();
  }, [loggedIn, seccion]); // eslint-disable-line react-hooks/exhaustive-deps

  function logout() {
    tokenOperario.borrar();
    post({ type: "sync", tokens: [], shipments: [] });
    setLoggedIn(false); setError(""); setAdding(false); setDraft(emptyShipment);
    setTokens(demoRepartidoresIniciales); setShipments(demoShipments.map((s) => ({ ...s })));
  }

async function registrarRepartidor(e: FormEvent) {
    e.preventDefault();
    setTokenGenerado(null);

    const invalido = validarRepartidor(driverDraft);
    if (invalido) { setTokenError(invalido); return; }
    setTokenError("");

    const tokenSession = tokenOperario.leer();
    if (!tokenSession) return;

    setRegistrando(true);
    try {
      const nuevo = await registrarRepartidorApi(tokenSession, {
        nombre: driverDraft.nombre.trim(),
        dni: driverDraft.dni,
        correo: driverDraft.correo.trim(),
        peso_max_kg: Number(driverDraft.peso_max_kg),
        alto_max_cm: Number(driverDraft.alto_max_cm),
        ancho_max_cm: Number(driverDraft.ancho_max_cm),
        largo_max_cm: Number(driverDraft.largo_max_cm),
      });
      // El código se ve una sola vez: en la base queda solo su hash.
      setTokenGenerado({ nombre: nuevo.nombre, codigo: nuevo.codigo_acceso });
      setDriverDraft(repartidorVacio);
      cargarRepartidores(); // la tabla se vuelve a pedir al backend, ya con el nuevo
    } catch (err) {
      setTokenError(manejarErrorDeSesion(err)); // p. ej. 409 "Ya existe un repartidor con ese DNI"
    } finally {
      setRegistrando(false);
    }
  }

  function addShipment(e: FormEvent) {
    e.preventDefault();
    setResultadoAltaEnvio(null);
    const r = shipmentSchema.safeParse(draft);
    if (!r.success) { setError(r.error.issues[0]?.message ?? "Revisá los datos."); return; }
    
    const guiaNueva = generateTrackingCode(shipments.map(s => s.guia));
    const pesoRequerido = r.data.pesoKg;
    
    const aptos = tokens.filter(t => t.habilitado && t.activo && t.pesoMaxKg >= pesoRequerido);
    
    if (aptos.length > 0) {
      const asignado = aptos[0]!;
      setShipments((rows) => [...rows, { ...r.data, guia: guiaNueva, repartidor: asignado.token, estado: "Repartidor asignado" }]);
      setResultadoAltaEnvio({ guia: guiaNueva, estado: "Repartidor asignado" });
    } else {
      setShipments((rows) => [...rows, { ...r.data, guia: guiaNueva, repartidor: undefined, estado: "Registrado" }]);
      setResultadoAltaEnvio({ guia: guiaNueva, estado: "Registrado", aviso: "No se encontró ningún repartidor activo habilitado para su peso y dimensiones." });
    }
    
    setAdding(false); setDraft(emptyShipment); setError("");
  }

  const driverLabel = (t?: string) => {
    const d = tokens.find((x) => x.token === t);
    return d ? `${d.token} · ${d.nombre}` : "Sin asignar";
  };

  const repartidoresFiltrados = repartidores.filter((rep) => {
    if (filtroHabilitacion === "habilitados") return rep.habilitado;
    if (filtroHabilitacion === "deshabilitados") return !rep.habilitado;
    return true;
  });

  if (verificandoSesion) {
    return <Shell role="Operario" title="Acceso de personal"><p className="fsub">Verificando sesión…</p></Shell>;
  }

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
        <Button type="button" variant={seccion === "repartidores" ? "default" : "outline"} className={seccion === "repartidores" ? "btn btn-primary" : "staff-secondary"} onClick={() => { setSeccion("repartidores"); setTokenGenerado(null); setTokenError(""); setResultadoAltaEnvio(null); }}>Sección de repartidores</Button>
      </div>

      {seccion === "repartidores" ? (
        <section aria-labelledby="repartidores-heading">
          <div className="form shipment-create" style={{ padding: 24, marginBottom: 32 }}>
            <h3 style={{ marginTop: 0, marginBottom: 20, fontSize: 18 }}>Alta de nuevo repartidor</h3>
            <form className="fgrid" onSubmit={registrarRepartidor} noValidate>
              <label className="full">Nombre<input value={driverDraft.nombre} onChange={(e) => setDriverDraft(v => ({ ...v, nombre: e.target.value }))} required /></label>
              {/* Solo números: se borra cualquier otra cosa que se tipee */}
              <label>DNI (sin puntos)<input inputMode="numeric" maxLength={8} value={driverDraft.dni} onChange={(e) => setDriverDraft(v => ({ ...v, dni: e.target.value.replace(/\D/g, "") }))} required /></label>
              <label>Correo electrónico<input type="email" value={driverDraft.correo} onChange={(e) => setDriverDraft(v => ({ ...v, correo: e.target.value }))} required /></label>

              {medidasRepartidor.map(([campo, etiqueta]) => (
                <label key={campo}>{etiqueta}<input type="number" step="0.1" min="0" value={driverDraft[campo]} onChange={(e) => setDriverDraft(v => ({ ...v, [campo]: e.target.value }))} required /></label>
              ))}

              {tokenError && <p className="staff-error full" role="alert">{tokenError}</p>}
              <div className="full" style={{ marginTop: 12 }}>
                <Button type="submit" className="btn btn-primary" disabled={registrando}><KeyRound />{registrando ? "Registrando…" : "Registrar y habilitar acceso"}</Button>
              </div>
            </form>
            {tokenGenerado && (
              <div className="demo-notice" style={{ marginTop: 24, borderLeftColor: "var(--m-red)", backgroundColor: "#fef2f2" }}>
                <strong>¡Alta exitosa!</strong> Entregale este código de acceso a {tokenGenerado.nombre}: <strong style={{ fontSize: 20, letterSpacing: "0.15em", marginLeft: 8 }}>{tokenGenerado.codigo}</strong>
                <br /><small>Anotalo ahora: por seguridad no se vuelve a mostrar.</small>
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

          {errorListado && <p className="staff-error" role="alert">{errorListado}</p>}
          <div className="shipment-table-wrap" style={{ marginTop: 16 }}>
            <table className="shipment-table">
              <caption>Nómina de repartidores</caption>
              <thead>
                <tr>
                  <th scope="col">Nombre</th><th scope="col">DNI</th><th scope="col">Carga habilitada</th><th scope="col">Habilitación</th><th scope="col">Disponibilidad</th>
                </tr>
              </thead>
              <tbody>
                {repartidoresFiltrados.length === 0 ? (
                  <tr><td colSpan={5} style={{ textAlign: "center", padding: 24 }}>No se encontraron repartidores para el filtro seleccionado.</td></tr>
                ) : (
                  repartidoresFiltrados.map((rep) => (
                    <tr key={rep.id}>
                      <th scope="row">
                        <strong style={{ display: "block" }}>{rep.nombre}</strong>
                        <small style={{ color: "var(--m-muted)" }}>{rep.correo}</small>
                      </th>
                      <td>{rep.dni}</td>
                      <td>{rep.peso_max_kg} kg — {rep.alto_max_cm} × {rep.ancho_max_cm} × {rep.largo_max_cm} cm <small style={{ display: "block", color: "var(--m-muted)" }}>alto × ancho × largo</small></td>
                      <td><span className="staff-status" style={{ background: rep.habilitado ? "#e6f4ea" : "#fce8e6", color: rep.habilitado ? "#137333" : "#c5221f" }}>{rep.habilitado ? "Habilitado" : "Deshabilitado"}</span></td>
                      <td><span className="staff-status" style={{ background: rep.activo ? "#e8f0fe" : "#f1f3f4", color: rep.activo ? "#1a73e8" : "#5f6368" }}>{rep.activo ? "Activo" : "Inactivo"}</span></td>
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
            <Button className="btn btn-primary" onClick={() => { setAdding(true); setError(""); setResultadoAltaEnvio(null); }}><PackagePlus />Subir envío</Button>
          </div>
          
          {resultadoAltaEnvio && (
            <div className="demo-notice" style={{ marginTop: 0, marginBottom: 24, borderLeftColor: "var(--m-orange)", backgroundColor: "#fff7ed" }}>
              <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
                <span><strong>¡Pedido registrado exitosamente!</strong></span>
                <span style={{ fontSize: 16 }}>Código de seguimiento: <strong style={{ letterSpacing: "0.1em" }}>{resultadoAltaEnvio.guia}</strong></span>
                <span>Estado: <strong>{resultadoAltaEnvio.estado}</strong></span>
                {resultadoAltaEnvio.aviso && <span style={{ color: "var(--m-red)" }}>{resultadoAltaEnvio.aviso}</span>}
              </div>
            </div>
          )}

          {adding && (
            <form className="form shipment-create" onSubmit={addShipment} noValidate>
              <div className="shipment-card-head">
                <h2>Nuevo envío</h2>
                <Button type="button" variant="ghost" size="icon" aria-label="Cerrar nuevo envío" onClick={() => { setAdding(false); setError(""); }}><X /></Button>
              </div>
              <div className="fgrid">
                {(Object.keys(fieldLabels) as Array<keyof typeof fieldLabels>).map((field) => (
                  <label className={field === "origen" || field === "destino" ? "full" : ""} key={field}>
                    {fieldLabels[field]}
                    <input 
                      type={field === "pesoKg" ? "number" : "text"}
                      step={field === "pesoKg" ? "0.1" : undefined}
                      value={draft[field] === 0 && field === "pesoKg" ? "" : draft[field]} 
                      onChange={(e) => setDraft((v) => ({ ...v, [field]: field === "pesoKg" ? Number(e.target.value) : e.target.value }))} 
                    />
                  </label>
                ))}
              </div>
              {error && <p className="staff-error" role="alert">{error}</p>}
              <Button type="submit" className="btn btn-primary staff-submit" style={{marginTop: 16}}><Check />Registrar pedido</Button>
            </form>
          )}

          <div className="shipment-table-wrap">
            <table className="shipment-table">
              <caption>Registro de envíos · Demostración</caption>
              <thead>
                <tr>{["Guía", "Origen", "Destino", "Destinatario", "Documento", "Peso / Medidas", "Estado"].map((n) => <th key={n} scope="col">{n}</th>)}</tr>
              </thead>
              <tbody>
                {shipments.map((s) => (
                  <tr key={s.guia}>
                    <th scope="row">{s.guia}</th>
                    <td>{s.origen}</td>
                    <td>{s.destino}</td>
                    <td>{s.destinatario}</td>
                    <td>{s.documentoReceptor}</td>
                    <td>{s.pesoKg} kg — {s.dimensiones}</td>
                    <td>
                      <span className="staff-status">{s.estado}</span>
                      {s.repartidor && <small style={{display: "block", marginTop: 6, color: "var(--m-muted)"}}>{driverLabel(s.repartidor)}</small>}
                      {s.fechaRetiro && <small style={{display: "block", marginTop: 4, color: "var(--m-blue)", fontSize: "0.75rem"}}>Retirado: {s.fechaRetiro}</small>}
                    </td>
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
