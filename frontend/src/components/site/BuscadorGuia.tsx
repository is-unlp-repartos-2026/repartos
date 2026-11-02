import { useState, type FormEvent, type ReactNode } from "react";
import { useNavigate } from "@tanstack/react-router";
import { Button } from "@/components/ui/button";

// El código de seguimiento tiene 8 letras y números (lo genera el backend al registrar el pedido).
const LARGO_GUIA = 8;

// Lo que no sea letra o número se descarta mientras se escribe, y todo pasa a mayúscula.
const limpiarGuia = (valor: string) => valor.toUpperCase().replace(/[^A-Z0-9]/g, "").slice(0, LARGO_GUIA);

// Buscador de la HU-21: lo usan el home y la página de seguimiento (para reintentar ahí mismo).
// El botón queda deshabilitado hasta que el código tenga los 8 caracteres.
export function BuscadorGuia({ inicial = "", onBuscar, children }: { inicial?: string; onBuscar?: () => void; children?: ReactNode }) {
  const navigate = useNavigate();
  const [guia, setGuia] = useState(limpiarGuia(inicial));
  const completa = guia.length === LARGO_GUIA;

  function buscar(e: FormEvent) {
    e.preventDefault();
    if (!completa) return;
    navigate({ to: "/seguimiento", search: { guia } }); // misma pestaña: el botón "atrás" del navegador vuelve
    onBuscar?.();
  }

  return (
    <form className="form" onSubmit={buscar} noValidate>
      {children}
      <div className="fgrid">
        <label className="full">Número de guía
          <input
            value={guia}
            onChange={(e) => setGuia(limpiarGuia(e.target.value))}
            placeholder="Ej: MF8K3TPM"
            autoComplete="off"
            style={{ letterSpacing: "0.15em" }}
          />
        </label>
      </div>
      <p className="hint">{completa ? "Si tenés dudas, comunicate con nuestra Casa Central." : `El número de guía tiene ${LARGO_GUIA} letras y números.`}</p>
      <Button type="submit" className="btn btn-primary" disabled={!completa}>Consultar estado</Button>
    </form>
  );
}
