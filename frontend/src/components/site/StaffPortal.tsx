import { useEffect, useRef, useState, type FormEvent } from "react";
import { useNavigate, useSearch } from "@tanstack/react-router";
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
import type { SeccionOperario } from "@/routes/operario";



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

// Solo un 401/403 significa que la sesión ya no vale (venció, código revocado o repartidor deshabilitado).
// Si el error es de conexión, la sesión se conserva: el repartidor puede estar sin señal en la calle.
const sesionInvalida = (err: unknown) => err instanceof ApiError && (err.status === 401 || err.status === 403);

// El código de acceso tiene 4 letras y números: lo demás se descarta mientras se escribe.
const LARGO_CODIGO_ACCESO = 4;
const limpiarCodigo = (valor: string) => valor.toUpperCase().replace(/[^A-Z0-9]/g, "").slice(0, LARGO_CODIGO_ACCESO);

// Pantalla que se ve si no se pudo verificar la sesión guardada porque el backend no responde.
function SinConexion({ mensaje, onReintentar }: { mensaje: string; onReintentar: () => void }) {
  return <div className="form staff-login">
    <p className="staff-error" role="alert">{mensaje}</p>
    <Button className="btn btn-primary staff-submit" onClick={onReintentar}>Reintentar</Button>
  </div>;
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
      {children}
    </div></main><Footer compact />
  </div>;
}

function DriverPortal() {
  // Reemplazamos el token simulado por el perfil real del backend
  const [repartidor, setRepartidor] = useState<Repartidor | null>(null);
  const [pending, setPending] = useState(false);
  const [error, setError] = useState("");
  const [codigo, setCodigo] = useState("");
  const [verificandoSesion, setVerificandoSesion] = useState(true);
  const [sinConexion, setSinConexion] = useState(false);
  
  // Mantenemos el estado de pedidos temporalmente (aunque quedará vacío hasta integrar la API de pedidos)
  const [state, setState] = useState<{ shipments: Shipment[] } | null>(null);
  const [pedidoSeleccionado, setPedidoSeleccionado] = useState<Shipment | null>(null);
  const [avisoFinJornada, setAvisoFinJornada] = useState("");

  const post = useChannel((m) => { if (m.type === "sync") setState({ shipments: m.shipments }); });

  // HU-02: al abrir la app, si hay una sesión guardada en el celular, entra directo.
  function verificarSesion() {
    const tokenGuardado = tokenRepartidor.leer();
    if (!tokenGuardado) { setVerificandoSesion(false); return; }
    setVerificandoSesion(true);
    setSinConexion(false);
    getSesionRepartidor(tokenGuardado)
      .then((perfil) => setRepartidor(perfil))
      .catch((err: Error) => {
        if (sesionInvalida(err)) tokenRepartidor.borrar(); // p. ej. lo deshabilitaron: vuelve al ingreso
        else setSinConexion(true);
        setError(err.message);
      })
      .finally(() => setVerificandoSesion(false));
  }

  useEffect(verificarSesion, []);

  async function login(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    if (codigo.length !== LARGO_CODIGO_ACCESO) return;
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
    setCodigo("");
  }

  // Al usar el backend real, el ID será un número entero. 
  // Las guías de prueba usan "RP01", por lo que esta lista se verá vacía hasta que se conecte el backend de envíos.
  const mine = repartidor && state ? state.shipments.filter((s) => s.repartidor === repartidor.id?.toString()) : [];
  
  function handleToggleDisponibilidad() {
    alert("Para cambiar la disponibilidad hay que integrar HU-13 (Comenzar jornada) y HU-14 (Terminar jornada).");
  }
  
  return (
    <Shell role="Repartidor" title={repartidor ? `Mis entregas - ${repartidor.nombre}` : "Acceso de repartidor"} onLogout={repartidor ? logout : undefined}>
      {verificandoSesion ? (
        <p className="fsub">Verificando sesión…</p>
      ) : sinConexion ? (
        <SinConexion mensaje={error} onReintentar={verificarSesion} />
      ) : !repartidor ? (
        <form className="form staff-login" onSubmit={login} noValidate>
          <h2>Ingresá tu código</h2>
          <div className="fgrid">
            <label className="full">Código de acceso (4 caracteres)
              <input value={codigo} onChange={(e) => setCodigo(limpiarCodigo(e.target.value))} autoComplete="off" style={{ letterSpacing: "0.3em" }} />
            </label>
          </div>
          {error && <p className="staff-error" role="alert">{error}</p>}
          <Button className="btn btn-primary staff-submit" type="submit" disabled={pending || codigo.length !== LARGO_CODIGO_ACCESO}>{pending ? "Verificando…" : "Ingresar"}<ArrowRight /></Button>
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

// Deja solo dígitos y un único punto decimal (acepta coma y la pasa a punto).
const soloDecimal = (valor: string) => valor.replace(",", ".").replace(/[^\d.]/g, "").replace(/(\..*)\./g, "$1");

// Las mismas reglas que el backend. Devuelve qué falta completar (o null si está todo bien):
// mientras falte algo, el botón de registrar queda deshabilitado.
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
  const [sinConexion, setSinConexion] = useState(false);
  const [error, setError] = useState("");
  const [usuario, setUsuario] = useState("");
  const [contrasena, setContrasena] = useState("");
  const [ingresando, setIngresando] = useState(false);
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

  // La sección sale de la URL (/operario?seccion=...): el "atrás" del navegador vuelve a la anterior.
  const seccion: SeccionOperario = useSearch({ from: "/operario" }).seccion ?? "repartidores";
  const navigate = useNavigate();
  const setSeccion = (nueva: SeccionOperario) => navigate({ to: "/operario", search: { seccion: nueva } });
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
  useEffect(verificarSesion, []);

  function verificarSesion() {
    const tokenGuardado = tokenOperario.leer();
    if (!tokenGuardado) { setVerificandoSesion(false); return; }
    setVerificandoSesion(true);
    setSinConexion(false);
    getSesionOperario(tokenGuardado)
      .then(() => setLoggedIn(true))
      .catch((err: Error) => {
        if (sesionInvalida(err)) tokenOperario.borrar(); // venció (30 min): vuelve al ingreso
        else { setSinConexion(true); setError(err.message); }
      })
      .finally(() => setVerificandoSesion(false));
  }

  // El botón queda deshabilitado hasta completar los dos campos (y mientras espera la respuesta).
  const puedeIngresar = usuario.trim() !== "" && contrasena !== "" && !ingresando;

  async function login(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    if (!puedeIngresar) return;
    setIngresando(true);
    try {
      const response = await loginOperario(usuario.trim(), contrasena);
      tokenOperario.guardar(response.token);
      setError("");
      setUsuario(""); setContrasena("");
      setLoggedIn(true);
    } catch (err) {
      // 401 → "Usuario o contraseña incorrectos" (lo manda el backend); sin conexión → el aviso de api.ts
      setError((err as Error).message);
    } finally {
      setIngresando(false);
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

  const faltaEnAlta = validarRepartidor(driverDraft);

  const repartidoresFiltrados = repartidores.filter((rep) => {
    if (filtroHabilitacion === "habilitados") return rep.habilitado;
    if (filtroHabilitacion === "deshabilitados") return !rep.habilitado;
    return true;
  });

  if (verificandoSesion) {
    return <Shell role="Operario" title="Acceso de personal"><p className="fsub">Verificando sesión…</p></Shell>;
  }

  if (sinConexion) {
    return <Shell role="Operario" title="Acceso de personal"><SinConexion mensaje={error} onReintentar={verificarSesion} /></Shell>;
  }

  if (!loggedIn) {
    return (
      <Shell role="Operario" title="Acceso de personal">
        <form className="form staff-login" onSubmit={login} noValidate>
          <h2>Ingresar como operario</h2>
          <div className="fgrid">
            <label className="full">Usuario<input value={usuario} onChange={(e) => setUsuario(e.target.value)} autoComplete="username" maxLength={100} /></label>
            <label className="full">Contraseña<input value={contrasena} onChange={(e) => setContrasena(e.target.value)} type="password" autoComplete="current-password" maxLength={128} /></label>
          </div>
          {error && <p className="staff-error" role="alert">{error}</p>}
          <Button className="btn btn-primary staff-submit" type="submit" disabled={!puedeIngresar}>{ingresando ? "Ingresando…" : "Ingresar"}<ArrowRight /></Button>
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
              <label className="full">Nombre<input value={driverDraft.nombre} maxLength={100} onChange={(e) => setDriverDraft(v => ({ ...v, nombre: e.target.value }))} /></label>
              {/* Solo números: se borra cualquier otra cosa que se tipee */}
              <label>DNI (sin puntos)<input inputMode="numeric" maxLength={8} value={driverDraft.dni} onChange={(e) => setDriverDraft(v => ({ ...v, dni: e.target.value.replace(/\D/g, "") }))} /></label>
              <label>Correo electrónico<input type="email" value={driverDraft.correo} maxLength={254} onChange={(e) => setDriverDraft(v => ({ ...v, correo: e.target.value }))} /></label>

              {/* Solo dígitos y un punto decimal: no se puede escribir "-5" ni "1e3" */}
              {medidasRepartidor.map(([campo, etiqueta]) => (
                <label key={campo}>{etiqueta}<input inputMode="decimal" value={driverDraft[campo]} onChange={(e) => setDriverDraft(v => ({ ...v, [campo]: soloDecimal(e.target.value) }))} /></label>
              ))}
              {tokenError && <p className="staff-error full" role="alert">{tokenError}</p>}
              <div className="full" style={{ marginTop: 12 }}>
                {/* Deshabilitado hasta que el formulario sea válido; arriba del botón se indica qué falta */}
                {faltaEnAlta && <p className="hint" style={{ marginTop: 0 }}>{faltaEnAlta}</p>}
                <Button type="submit" className="btn btn-primary" disabled={registrando || faltaEnAlta !== null}><KeyRound />{registrando ? "Registrando…" : "Registrar y habilitar acceso"}</Button>
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
        // El registro de pedidos (HU-04) y el tablero (HU-22) todavía no están conectados al backend.
        <p className="demo-notice">Registro de pedidos y tablero de envíos: próximamente.</p>
      )}
    </Shell>
  );
}
