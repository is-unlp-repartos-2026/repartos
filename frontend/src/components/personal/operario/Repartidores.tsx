// Sección de repartidores del operario:
//   HU-09 alta (el botón queda deshabilitado hasta que el formulario sea válido)
//   HU-10 listado con filtro por habilitación
//   HU-11 modificar la carga habilitada
//   HU-12 habilitar / deshabilitar (cada botón aparece solo cuando corresponde)
import { useEffect, useState, type FormEvent } from "react";
import { KeyRound } from "lucide-react";
import { Button } from "@/components/ui/button";
import {
  deshabilitarRepartidor, habilitarRepartidor, listarRepartidores, modificarHabilitacion,
  registrarRepartidor, type Repartidor,
} from "@/lib/api";
import { correoValido, dniValido, formatearMedidas, soloDecimal, soloDigitos, validarMedidas } from "@/lib/formato";
import { Aviso, Ventana, type SesionActiva } from "../comun";

const MEDIDAS = [
  ["peso_max_kg", "Peso máx (kg)"], ["alto_max_cm", "Alto máx (cm)"], ["ancho_max_cm", "Ancho máx (cm)"], ["largo_max_cm", "Largo máx (cm)"],
] as const;

type Carga = { peso_max_kg: string; alto_max_cm: string; ancho_max_cm: string; largo_max_cm: string };
type Borrador = Carga & { nombre: string; dni: string; correo: string };
const VACIO: Borrador = { nombre: "", dni: "", correo: "", peso_max_kg: "", alto_max_cm: "", ancho_max_cm: "", largo_max_cm: "" };

// Las mismas reglas que el backend. Devuelve qué falta completar, o null si está todo bien.
function queFalta(d: Borrador): string | null {
  if (!d.nombre.trim()) return "Completá el nombre.";
  if (!dniValido(d.dni)) return "El DNI tiene que tener 7 u 8 números, sin puntos.";
  if (!correoValido(d.correo)) return "Ingresá un correo válido.";
  return validarMedidas(d, MEDIDAS);
}

const cargaANumeros = (c: Carga) => ({
  peso_max_kg: Number(c.peso_max_kg), alto_max_cm: Number(c.alto_max_cm), ancho_max_cm: Number(c.ancho_max_cm), largo_max_cm: Number(c.largo_max_cm),
});

type Filtro = "todos" | "habilitados" | "deshabilitados";

export function Repartidores({ sesion }: { sesion: SesionActiva }) {
  const [repartidores, setRepartidores] = useState<Repartidor[]>([]);
  const [filtro, setFiltro] = useState<Filtro>("todos");
  const [aviso, setAviso] = useState("");
  const [error, setError] = useState("");
  const [editando, setEditando] = useState<Repartidor | null>(null);
  const [aDeshabilitar, setADeshabilitar] = useState<Repartidor | null>(null);

  function cargar() {
    listarRepartidores(sesion.token)
      .then((r) => { setRepartidores(r); setError(""); })
      .catch((err) => setError(sesion.manejarError(err)));
  }
  useEffect(cargar, []); // eslint-disable-line react-hooks/exhaustive-deps

  // Después de cualquier cambio se muestra el resultado y se vuelve a pedir la lista al backend.
  function listo(texto: string) {
    setEditando(null);
    setADeshabilitar(null);
    setAviso(texto);
    setError("");
    cargar();
  }

  async function habilitar(r: Repartidor) {
    try {
      await habilitarRepartidor(sesion.token, r.id);
      listo(`${r.nombre} quedó habilitado: ya puede volver a ingresar a la app.`);
    } catch (err) {
      setError(sesion.manejarError(err));
    }
  }

  const visibles = repartidores.filter((r) => filtro === "todos" || (filtro === "habilitados") === r.habilitado);

  return (
    <section aria-labelledby="repartidores-titulo">
      <AltaRepartidor sesion={sesion} onAlta={cargar} />

      <div className="staff-toolbar" style={{ flexWrap: "wrap", gap: 16 }}>
        <div>
          <h2 id="repartidores-titulo" style={{ margin: 0, fontSize: 20 }}>Listado de repartidores</h2>
          <p style={{ margin: 0, color: "var(--m-muted)" }}>Mostrando {visibles.length} repartidores</p>
        </div>
        <label style={{ display: "flex", alignItems: "center", gap: 8, fontSize: 14, fontWeight: 500 }}>Filtrar por habilitación:
          <select value={filtro} onChange={(e) => setFiltro(e.target.value as Filtro)} style={{ padding: "6px 12px", borderRadius: 6, border: "1px solid #ccc" }}>
            <option value="todos">Todos</option>
            <option value="habilitados">Habilitados</option>
            <option value="deshabilitados">Deshabilitados</option>
          </select>
        </label>
      </div>
      <Aviso texto={aviso} />
      <Aviso texto={error} error />

      <div className="shipment-table-wrap" style={{ marginTop: 16 }}>
        <table className="shipment-table">
          <thead>
            <tr><th scope="col">Nombre</th><th scope="col">DNI</th><th scope="col">Carga habilitada</th><th scope="col">Habilitación</th><th scope="col">Disponibilidad</th><th scope="col">Acciones</th></tr>
          </thead>
          <tbody>
            {visibles.length === 0 ? (
              <tr><td colSpan={6} style={{ textAlign: "center", padding: 24 }}>No hay repartidores para el filtro seleccionado.</td></tr>
            ) : visibles.map((r) => (
              <tr key={r.id}>
                <th scope="row"><strong style={{ display: "block" }}>{r.nombre}</strong><small style={{ color: "var(--m-muted)" }}>{r.correo}</small></th>
                <td>{r.dni}</td>
                <td>{r.peso_max_kg} kg — {formatearMedidas(r.alto_max_cm, r.ancho_max_cm, r.largo_max_cm)}<small style={{ display: "block", color: "var(--m-muted)" }}>alto × ancho × largo</small></td>
                <td><span className="staff-status" style={{ background: r.habilitado ? "#e6f4ea" : "#fce8e6", color: r.habilitado ? "#137333" : "#c5221f" }}>{r.habilitado ? "Habilitado" : "Deshabilitado"}</span></td>
                <td><span className="staff-status" style={{ background: r.activo ? "#e8f0fe" : "#f1f3f4", color: r.activo ? "#1a73e8" : "#5f6368" }}>{r.activo ? "Activo" : "Inactivo"}</span></td>
                <td>
                  <div className="staff-actions" style={{ gap: 8 }}>
                    <Button size="sm" variant="outline" onClick={() => { setAviso(""); setEditando(r); }}>Modificar carga</Button>
                    {r.habilitado
                      ? <Button size="sm" variant="outline" onClick={() => { setAviso(""); setADeshabilitar(r); }}>Deshabilitar</Button>
                      : <Button size="sm" variant="outline" onClick={() => habilitar(r)}>Habilitar</Button>}
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {editando && <ModificarCarga repartidor={editando} sesion={sesion} onCerrar={() => setEditando(null)} onListo={listo} />}
      {aDeshabilitar && <ConfirmarDeshabilitar repartidor={aDeshabilitar} sesion={sesion} onCerrar={() => setADeshabilitar(null)} onListo={listo} />}
    </section>
  );
}

// HU-09: el código de acceso se muestra una sola vez (en la base queda solo su hash).
function AltaRepartidor({ sesion, onAlta }: { sesion: SesionActiva; onAlta: () => void }) {
  const [borrador, setBorrador] = useState<Borrador>(VACIO);
  const [enviando, setEnviando] = useState(false);
  const [error, setError] = useState("");
  const [generado, setGenerado] = useState<{ nombre: string; codigo: string } | null>(null);
  const falta = queFalta(borrador);

  const campo = (nombre: keyof Borrador, limpiar: (v: string) => string = (v) => v) =>
    ({ value: borrador[nombre], onChange: (e: { target: { value: string } }) => setBorrador((b) => ({ ...b, [nombre]: limpiar(e.target.value) })) });

  async function registrar(e: FormEvent) {
    e.preventDefault();
    if (falta || enviando) return;
    setEnviando(true);
    setError("");
    setGenerado(null);
    try {
      const nuevo = await registrarRepartidor(sesion.token, {
        nombre: borrador.nombre.trim(), dni: borrador.dni, correo: borrador.correo.trim(), ...cargaANumeros(borrador),
      });
      setGenerado({ nombre: nuevo.nombre, codigo: nuevo.codigo_acceso });
      setBorrador(VACIO);
      onAlta();
    } catch (err) {
      setError(sesion.manejarError(err)); // p. ej. 409 "Ya existe un repartidor con ese DNI"
    } finally {
      setEnviando(false);
    }
  }

  return (
    <div className="form shipment-create" style={{ padding: 24, marginBottom: 32 }}>
      <h2>Alta de nuevo repartidor</h2>
      <form className="fgrid" onSubmit={registrar} noValidate>
        <label className="full">Nombre<input maxLength={100} {...campo("nombre")} /></label>
        <label>DNI (sin puntos)<input inputMode="numeric" {...campo("dni", (v) => soloDigitos(v, 8))} /></label>
        <label>Correo electrónico<input type="email" maxLength={254} {...campo("correo")} /></label>
        {MEDIDAS.map(([nombre, etiqueta]) => (
          <label key={nombre}>{etiqueta}<input inputMode="decimal" {...campo(nombre, soloDecimal)} /></label>
        ))}
        <div className="full" style={{ marginTop: 12 }}>
          <Aviso texto={error} error />
          {falta && <p className="hint" style={{ marginTop: 0 }}>{falta}</p>}
          <Button type="submit" className="btn btn-primary" disabled={!!falta || enviando}><KeyRound />{enviando ? "Registrando…" : "Registrar y habilitar acceso"}</Button>
        </div>
      </form>
      {generado && (
        <div className="demo-notice" role="status" style={{ marginTop: 24, borderLeftColor: "var(--m-red)", backgroundColor: "#fef2f2" }}>
          <strong>¡Alta exitosa!</strong> Entregale este código de acceso a {generado.nombre}: <strong style={{ fontSize: 20, letterSpacing: "0.15em", marginLeft: 8 }}>{generado.codigo}</strong>
          <br /><small>Anotalo ahora: por seguridad no se vuelve a mostrar.</small>
        </div>
      )}
    </div>
  );
}

type PropsVentana = { repartidor: Repartidor; sesion: SesionActiva; onCerrar: () => void; onListo: (aviso: string) => void };

// HU-11: si tiene pedidos en curso, el backend no lo permite y se muestra su aviso (es un criterio de aceptación).
function ModificarCarga({ repartidor, sesion, onCerrar, onListo }: PropsVentana) {
  const [carga, setCarga] = useState<Carga>({
    peso_max_kg: String(repartidor.peso_max_kg), alto_max_cm: String(repartidor.alto_max_cm),
    ancho_max_cm: String(repartidor.ancho_max_cm), largo_max_cm: String(repartidor.largo_max_cm),
  });
  const [enviando, setEnviando] = useState(false);
  const [error, setError] = useState("");
  const nueva = cargaANumeros(carga);
  const sinCambios = MEDIDAS.every(([c]) => nueva[c] === repartidor[c]);
  const falta = validarMedidas(carga, MEDIDAS) ?? (sinCambios ? "Cambiá algún valor para poder guardar." : null);

  async function guardar() {
    setEnviando(true);
    try {
      await modificarHabilitacion(sesion.token, repartidor.id, nueva);
      onListo(`Se guardó la nueva carga de ${repartidor.nombre}: se usa en las próximas asignaciones.`);
    } catch (err) {
      setError(sesion.manejarError(err));
      setEnviando(false);
    }
  }

  return (
    <Ventana abierta titulo={`Modificar carga de ${repartidor.nombre}`} descripcion="Peso y medidas máximas que puede transportar." onCerrar={onCerrar}>
      <div className="fgrid">
        {MEDIDAS.map(([nombre, etiqueta]) => (
          <label key={nombre}>{etiqueta}<input inputMode="decimal" value={carga[nombre]} onChange={(e) => setCarga((c) => ({ ...c, [nombre]: soloDecimal(e.target.value) }))} /></label>
        ))}
      </div>
      {falta && <p className="hint" style={{ margin: 0 }}>{falta}</p>}
      <Aviso texto={error} error />
      <div className="staff-actions">
        <Button className="btn btn-primary" disabled={!!falta || enviando} onClick={guardar}>{enviando ? "Guardando…" : "Guardar"}</Button>
        <Button variant="outline" className="staff-secondary" onClick={onCerrar}>Cancelar</Button>
      </div>
    </Ventana>
  );
}

// HU-12: al deshabilitar, sus pedidos sin retirar se reasignan. Con pedidos en camino el backend no lo permite
// y se muestra su aviso (es un criterio de aceptación).
function ConfirmarDeshabilitar({ repartidor, sesion, onCerrar, onListo }: PropsVentana) {
  const [enviando, setEnviando] = useState(false);
  const [error, setError] = useState("");

  async function deshabilitar() {
    setEnviando(true);
    try {
      const r = await deshabilitarRepartidor(sesion.token, repartidor.id);
      onListo(`${repartidor.nombre} quedó deshabilitado. Pedidos reasignados: ${r.pedidos_reasignados}. Sin repartidor (vuelven a Registrado): ${r.pedidos_sin_repartidor}.`);
    } catch (err) {
      setError(sesion.manejarError(err));
      setEnviando(false);
    }
  }

  return (
    <Ventana abierta titulo={`¿Deshabilitar a ${repartidor.nombre}?`}
      descripcion="No va a poder ingresar a la app ni recibir pedidos. Los pedidos que tiene asignados (sin retirar) se reasignan a otro repartidor apto. Su historial se conserva." onCerrar={onCerrar}>
      <Aviso texto={error} error />
      <div className="staff-actions">
        <Button className="btn btn-primary" disabled={enviando} onClick={deshabilitar}>{enviando ? "Deshabilitando…" : "Sí, deshabilitar"}</Button>
        <Button variant="outline" className="staff-secondary" onClick={onCerrar}>No, volver</Button>
      </div>
    </Ventana>
  );
}
