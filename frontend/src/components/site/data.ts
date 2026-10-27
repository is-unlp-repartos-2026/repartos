// Contenido estático de la página (separado para editar fácilmente).
export const nav = [
  { t: "Servicios", href: "#servicios" },
  { t: "Cobertura", href: "#cobertura" },
  { t: "Seguí tu pedido", href: "#seguimiento" },
] as const;

export const beneficios = [
  { icon: "shield", t: "Seguridad", d: "Cuidamos tu carga en cada recorrido." },
  { icon: "clock", t: "Puntualidad", d: "Entregas coordinadas en los plazos acordados." },
  { icon: "pin", t: "Cobertura nacional", d: "Redespachos con otros transportes en el país." },
  { icon: "headset", t: "Atención personalizada", d: "Un equipo disponible para cada consulta." },
] as const;

export const servicios = [
  { t: "Encomiendas", d: "Despacho de paquetes y bultos con una operatoria simple, directa y pensada para entregas frecuentes." },
  { t: "Cargas generales", d: "Traslado de mercadería y cargas de distinto volumen según coordinación previa." },
  { t: "Envíos express", d: "Entregas rápidas en 24 o 48 horas, según el origen, el destino y la coordinación operativa." },
  { t: "Distribución comercial", d: "Soporte logístico para negocios que necesitan abastecer o entregar mercadería regularmente." },
  { t: "Redespachos nacionales", d: "Combinamos el envío con otros transportes para alcanzar destinos en las demás provincias de la Argentina." },
];

export const bases = [
  { n: "Capital Federal", tag: "Casa Central" },
  { n: "La Plata", tag: "Sucursal" },
  { n: "Mar de Ajó", tag: "Sucursal" },
  { n: "Villa Gesell", tag: "Sucursal" },
];

const s = (x: string) => x.split(",").map((v) => v.trim());

export const laPlata = s("Buenos Aires,Capital Federal,Ensenada,Berisso,La Plata,Magdalena,Bartolomé Bavio,Vieytes,Verónica,Pipinas,Brandsen,San Miguel del Monte,Cañuelas,San Vicente,Alejandro Korn,Ranchos,General Belgrano,Pila,Chascomús,Lezama,Castelli,Dolores");
export const costa = s("Mar del Plata,Mar de Ajó,Santa Teresita,San Bernardo,Costa del Este,Aguas Verdes,La Lucila del Mar,San Clemente del Tuyú,Las Toninas,Costa Azul,San Bernardo del Tuyú,Mar del Tuyú,General Madariaga,Pinamar,Ostende,Valeria del Mar,Villa Gesell,Mar de las Pampas");
export const amba = [
  { z: "Zona Sur", dias: "Martes y viernes", l: s("Adrogué,Avellaneda,Banfield,Berazategui,Bernal,Burzaco,Claypole,Dock Sud,Don Bosco,Ezpeleta,Florencio Varela,Gerli,José Mármol,Lanús,Lavallol,Lomas de Zamora,Monte Chingolo,Monte Grande,Piñeyro,Quilmes,Rafael Calzada,Remedios de Escalada,San Francisco Solano,Sarandí,Temperley,Valentín Alsina,Villa Domínico,Wilde") },
  { z: "Zona Norte", dias: "Lunes y jueves", l: s("Acassuso,Beccar,Boulogne,Carapachay,Caseros,Don Torcuato,Florida,General Pacheco,José León Suárez,Martín Coronado,Martínez,Munro,Villa Martelli,Olivos,Pablo Podestá,Sáenz Peña,San Andrés,San Fernando,San Isidro,San Martín,Santos Lugares,Tigre,Vicente López,Victoria,Villa Adelina,Villa Ballester,Villa Bosch,Villa Lynch,Virreyes,Loma Hermosa") },
  { z: "Zona Oeste", dias: "Miércoles", l: s("Aldo Bonzi,Castelar,Ciudadela,Ciudad Evita,Haedo,Hurlingham,Isidro Casanova,Ituzaingó,José Ingenieros,Laferrere,Libertad,Lomas del Mirador,Merlo,Moreno,Morón,Padua,Palomar,Paso del Rey,Rafael Castillo,Ramos Mejía,San Justo,Tablada,Tapiales,Villa Madero,Villa Tesei,Villa Celina") },
];

export const empresas = [
  { t: "Coordinación ágil", d: "Canal de atención para organizar retiros, despachos y entregas." },
  { t: "Frecuencia diaria", d: "Una dinámica pensada para operaciones que no pueden detenerse." },
  { t: "Escala flexible", d: "Alternativas para distintos volúmenes y tipos de mercadería." },
  { t: "Atención comercial", d: "Seguimiento cercano para construir una relación de trabajo sostenida." },
];

export const pasos = [
  { t: "Relevamiento", d: "Conocemos la necesidad y el tipo de operación." },
  { t: "Coordinación", d: "Definimos la alternativa de servicio adecuada." },
  { t: "Operación", d: "Integramos el envío al circuito correspondiente." },
];

export const sucursales = [
  { n: "Capital Federal", cc: true, dir: "Los Patos 2548/66", tel: ["(011) 4942-2627", "6686"], wa: "11 6742-7165", mail: "capital@transportemorabito.com.ar" },
  { n: "La Plata", dir: "139 N° 1661 (515 y 516)", tel: ["(0221) 470-7624", "470-2389"], wa: "221 317-7906", mail: "laplata@transportemorabito.com.ar" },
  { n: "Mar de Ajó", dir: "Av. del Libertador 1945", tel: ["(02257) 420534", "429033"], wa: "2257 668-611", mail: "mardeajo@transportemorabito.com.ar" },
  { n: "Villa Gesell", dir: "Av. Buenos Aires y Circunvalación", tel: ["(02255) 458588"], mail: "vgesell@transportemorabito.com.ar" },
];
