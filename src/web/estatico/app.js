/* Demostrador del departamento antifraude.
   Sin dependencias externas: el TFG se ejecuta sin conexion y la interfaz
   tambien debe hacerlo. */

const $ = (s) => document.querySelector(s);

async function api(ruta, opciones) {
  const r = await fetch(ruta, opciones);
  const cuerpo = await r.json().catch(() => ({}));
  if (!r.ok) throw new Error(cuerpo.detail || `Error ${r.status}`);
  return cuerpo;
}

function post(ruta, datos) {
  return api(ruta, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(datos || {}),
  });
}

/* Turno actualmente cargado en el servidor.
   Las pantallas 2 y 3 piden un numero de caso, y sin saber de que expediente
   ese numero no significa nada. En las pruebas, un turno que fallo dejo
   cargado el anterior y la interfaz respondia "el caso 55 no existe" sin
   decir que el expediente vigente solo llegaba al 32. */
let TURNO = null;

function pintarBarraTurno() {
  const b = $("#turno-activo");
  if (!TURNO) {
    b.className = "turno-activo";
    b.innerHTML = `<span class="aviso-sin-turno">No hay ningún turno cargado.
      Ve a la pantalla 1 y pulsa Detectar.</span>`;
    return;
  }
  const p = TURNO.parametros, r = TURNO.resumen;
  b.className = "turno-activo";
  b.innerHTML =
    `<span>Turno activo: <b>${p.horas} h</b> desde +<b>${p.desplazamiento} h</b></span>
     <span>umbral <b>${p.umbral}</b></span>
     <span>capacidad <b>${p.capacidad}</b></span>
     <span><b>${r.casos_elevados}</b> casos en el expediente
       (numerados del 1 al ${r.casos_elevados})</span>
     <span><b>${r.fraude_en_expediente}</b> son fraude real</span>`;
  // Los selectores de caso se acotan al expediente vigente, para que no se
  // pueda pedir un caso que no existe.
  ["#n-caso", "#n-inv"].forEach((s) => {
    const el = $(s);
    el.max = r.casos_elevados;
    if (+el.value > r.casos_elevados) el.value = r.casos_elevados;
  });
}

/* --- Navegacion por pasos --- */
document.querySelectorAll(".paso").forEach((b) => {
  b.onclick = () => {
    document.querySelectorAll(".paso").forEach((x) => x.classList.remove("activo"));
    document.querySelectorAll(".panel").forEach((x) => x.classList.remove("visible"));
    b.classList.add("activo");
    $("#" + b.dataset.panel).classList.add("visible");
  };
});

/* --- Estado del entorno --- */
async function comprobarEstado() {
  try {
    const e = await api("/api/estado");
    const marca = (ok, txt) =>
      `<span class="${ok ? "ok" : "mal"}">${ok ? "✓" : "✗"} ${txt}</span>`;
    $("#estado").innerHTML =
      marca(e.dataset, "conjunto de datos") +
      marca(e.modelo_detector, "detector entrenado") +
      marca(e.ollama, e.ollama ? `Ollama (${e.modelos_llm.length} modelos)` : "Ollama no responde");

    const opciones = e.modelos_llm.length
      ? e.modelos_llm.map((m) => `<option ${m === e.modelo_por_defecto ? "selected" : ""}>${m}</option>`).join("")
      : `<option value="">sin modelos</option>`;
    $("#modelo-inv").innerHTML = opciones;
    $("#modelo-inf").innerHTML = opciones;

    // Se recupera el turno que el servidor tenga cargado. Sin esto, recargar
    // la pagina dejaba al cliente creyendo que no habia expediente mientras
    // el servidor seguia con el anterior.
    TURNO = e.turno;
    pintarBarraTurno();
    if (TURNO) {
      $("#horas").value = TURNO.parametros.horas;
      $("#desp").value = TURNO.parametros.desplazamiento;
      $("#umbral").value = TURNO.parametros.umbral;
      $("#capacidad").value = TURNO.parametros.capacidad;
    }
  } catch (err) {
    $("#estado").innerHTML = `<span class="mal">✗ ${err.message}</span>`;
    pintarBarraTurno();
  }
}

/* --- 1. Turno --- */
$("#btn-turno").onclick = async function () {
  this.disabled = true;
  this.textContent = "Detectando…";
  try {
    const d = await post("/api/turno", {
      horas: +$("#horas").value,
      desplazamiento: +$("#desp").value,
      umbral: +$("#umbral").value,
      capacidad: +$("#capacidad").value,
    });
    TURNO = d;
    pintarBarraTurno();
    const r = d.resumen;
    $("#resumen-turno").innerHTML = [
      ["transacciones", r.transacciones.toLocaleString("es"), ""],
      ["fraudes en el turno", r.fraudes_reales, ""],
      ["casos elevados", r.casos_elevados, "destacada"],
      ["de ellos, fraude", r.fraude_en_expediente, ""],
      ["detección", r.ms_deteccion + " ms", ""],
    ].map(([et, v, cl]) =>
      `<div class="tarjeta ${cl}"><div class="valor">${v}</div>
       <div class="etiqueta">${et}</div></div>`).join("");

    $("#tabla-casos").innerHTML = `<div class="tabla-scroll"><table><thead><tr>
      <th>#</th><th>Identificador</th><th class="num">Probabilidad</th>
      <th>Riesgo</th><th class="num">Importe</th><th class="num">Hora</th>
      <th>Clase real</th></tr></thead><tbody>` +
      d.casos.map((c) => `<tr class="${c.es_fraude ? "fraude" : ""}"
          onclick="verCaso(${c.n})">
        <td>${c.n}</td><td>${c.id}</td>
        <td class="num">${c.probabilidad.toFixed(4)}</td>
        <td><span class="pastilla ${c.riesgo.toLowerCase()}">${c.riesgo}</span></td>
        <td class="num">${c.importe.toFixed(2)} €</td>
        <td class="num">${c.hora.toFixed(1)} h</td>
        <td>${c.es_fraude ? "<b>FRAUDE</b>" : "legítima"}</td></tr>`).join("") +
      `</tbody></table></div>
       <p class="nota">La columna de clase real no la ve el sistema en ningún
        momento: se muestra sólo para poder juzgar sus decisiones. Pulsa una
        fila para inspeccionar el caso.</p>`;
  } catch (err) {
    // Se limpia el resumen anterior: dejarlo junto a un mensaje de error hacia
    // creer que las cifras correspondian al turno recien pedido.
    $("#resumen-turno").innerHTML = "";
    $("#tabla-casos").innerHTML =
      `<div class="alerta">${err.message}</div>` +
      (TURNO ? `<p class="nota">Sigue cargado el turno anterior, indicado en
        la barra azul de arriba.</p>` : "");
    pintarBarraTurno();
  }
  this.disabled = false;
  this.textContent = "Detectar";
};

/* Recuerda al usuario que casos hay realmente, que es la informacion que
   faltaba cuando la interfaz decia unicamente "el caso 55 no existe". */
function rangoValido() {
  if (!TURNO) return ` No hay ningún turno cargado: ve a la pantalla 1.`;
  return ` El expediente actual va del caso 1 al
    ${TURNO.resumen.casos_elevados}.`;
}

/* --- 2. Caso --- */
window.verCaso = function (n) {
  $("#n-caso").value = n;
  $("#n-inv").value = n;
  document.querySelector('[data-panel="p-caso"]').click();
  $("#btn-caso").click();
};

$("#btn-caso").onclick = async function () {
  try {
    const n = +$("#n-caso").value;
    const d = await api(`/api/caso/${n}?dossier=${$("#nivel-dossier").value}`);
    const max = Math.max(...d.contribuciones.map((c) => Math.abs(c.aporte)));

    $("#detalle-caso").innerHTML = `
      <div class="cuadro">
        <div class="tarjetas" style="margin:0 0 14px">
          <div class="tarjeta"><div class="valor">${d.probabilidad.toFixed(4)}</div>
            <div class="etiqueta">probabilidad</div></div>
          <div class="tarjeta"><div class="valor">${d.importe.toFixed(2)} €</div>
            <div class="etiqueta">importe</div></div>
          <div class="tarjeta"><div class="valor">${d.hora.toFixed(1)} h</div>
            <div class="etiqueta">hora del día</div></div>
          <div class="tarjeta ${d.es_fraude ? "destacada" : ""}">
            <div class="valor">${d.es_fraude ? "FRAUDE" : "legítima"}</div>
            <div class="etiqueta">clase real</div></div>
        </div>
        <h3>Contribuciones por variable</h3>
        ${d.contribuciones.map((c) => {
          const ancho = (Math.abs(c.aporte) / max) * 50;
          const pos = c.aporte > 0;
          return `<div class="contrib">
            <span class="var">${c.variable}</span>
            <span class="barra"><span class="relleno ${pos ? "pos" : "neg"}"
              style="left:${pos ? 50 : 50 - ancho}%;width:${ancho}%"></span></span>
            <span class="cifra">${c.aporte >= 0 ? "+" : ""}${c.aporte.toFixed(3)}</span>
          </div>`;
        }).join("")}
        <p class="nota">En rojo, hacia fraude. En azul, hacia legítima.</p>
      </div>`;
    $("#dossier").textContent = d.dossier;
  } catch (err) {
    $("#detalle-caso").innerHTML =
      `<div class="alerta">${err.message}${rangoValido()}</div>`;
    $("#dossier").textContent = "";
  }
};

/* --- 3. Investigacion --- */
$("#btn-inv").onclick = async function () {
  this.disabled = true;
  this.textContent = "Consultando al modelo…";
  $("#aviso-inv").innerHTML = "";
  try {
    const n = +$("#n-inv").value;
    const d = await post(`/api/investigar/${n}`, {
      modelo: $("#modelo-inv").value || null,
      dominio: $("#dominio").checked,
      max_tokens: +$("#max-tokens").value,
    });

    $("#prosa").innerHTML = d.prosa
      ? d.prosa.replace(/\n/g, "<br>")
      : "<i>sin texto</i>";

    const v = d.veredicto;
    const clase = v ? v.toLowerCase() : "ninguno";
    // Un descarte sobre un caso que es fraude real destruye deteccion: se
    // senala de forma explicita porque es el fallo que mide la memoria.
    const destruye = v === "DESCARTADO" && d.es_fraude;
    $("#veredicto").innerHTML = `
      <div class="veredicto-grande ${clase}">${v || "no reconocido"}</div>
      <p class="nota">${d.segundos} s · ${d.modelo}${d.dominio ? " · con corrección de dominio" : ""}${
        d.tokens_generados ? ` · ${d.tokens_generados} tokens` : ""}${
        d.truncado ? ` · <b style="color:var(--ambar)">respuesta truncada</b>` : ""}</p>
      ${destruye ? `<div class="alerta" style="margin:14px 0 0">
        Este caso <b>era fraude real</b> y el modelo lo ha retirado del informe.
        Es exactamente el fallo que la memoria cuantifica: el sistema detecta
        menos con la capa 2 que sin ella.</div>` : ""}
      ${v === "CONFIRMADO" && !d.es_fraude ? `<div class="aviso" style="margin:14px 0 0">
        Falso positivo confirmado: consume revisión humana sin motivo.</div>` : ""}`;

    if (d.aviso) $("#aviso-inv").innerHTML = `<div class="aviso">${d.aviso}</div>`;
    $("#prompt-inv").textContent = d.prompt;
  } catch (err) {
    $("#aviso-inv").innerHTML =
      `<div class="alerta">${err.message}${rangoValido()}</div>`;
  }
  this.disabled = false;
  this.textContent = "Investigar";
};

/* Nombres legibles de las metricas. Las claves internas -n_lote,
   n_fraude_descartado- son utiles en un fichero de resultados y opacas en
   pantalla. */
const ETIQUETAS = {
  n_lote: "transacciones del turno",
  fraudes_totales: "fraudes reales",
  casos_elevados: "casos elevados",
  fraudes_elevados: "fraude en el expediente",
  recall_detector: "recall del detector",
  precision_detector: "precisión del detector",
  n_confirmados: "confirmados por el modelo",
  n_descartados: "descartados por el modelo",
  n_fraude_descartado: "FRAUDE DESTRUIDO",
  n_descarte_correcto: "descartes acertados",
  recall_sistema: "recall del sistema",
  precision_sistema: "precisión del sistema",
};

/* --- 4. Informe --- */
$("#btn-informe").onclick = async function () {
  this.disabled = true;
  this.textContent = "Ejecutando los seis agentes…";
  $("#auditoria").innerHTML =
    `<div class="aviso">Esto tarda varios minutos. El coste está en la capa 2:
     la detección de la pantalla 1 fueron milisegundos.</div>`;
  try {
    const d = await post("/api/informe", {
      modelo: $("#modelo-inf").value || null,
      modo: $("#modo").value,
    });
    const a = d.auditoria;
    // El auditor devuelve TRES veredictos, no dos: FIABLE, INCOMPLETO y
    // NO FIABLE con su motivo. La primera version los reducia a fiable o no
    // fiable, de modo que un informe INCOMPLETO -que en modo interpreta es lo
    // esperado, porque ahi no se emiten veredictos- aparecia en rojo como si
    // hubiera inventado datos. Se muestra el veredicto literal y sus razones.
    const v = a.veredicto || (a.fiable ? "FIABLE" : "NO FIABLE");
    const clase = v === "FIABLE" ? "bien" : (v === "INCOMPLETO" ? "aviso" : "alerta");
    const cob = Math.round((a.cobertura ?? 0) * 100);

    const razones = [];
    const total = TURNO ? TURNO.resumen.casos_elevados : a.ids_cubiertos.length;
    razones.push(`Cobertura del expediente: <b>${cob} %</b> —
      ${a.ids_cubiertos.length} de ${total} casos citados en el informe.`);
    if (a.ids_inventados.length)
      razones.push(`<b>Identificadores inventados:</b> ${a.ids_inventados.join(", ")}
        — el informe habla de transacciones que no existen.`);
    if (a.ids_fuera_expediente.length)
      razones.push(`Cita casos del lote que no estaban en el expediente:
        ${a.ids_fuera_expediente.join(", ")}`);
    if (a.conceptos_inventados.length)
      razones.push(`<b>Invención semántica:</b> ` + a.conceptos_inventados
        .map(([texto, motivo]) => `«${texto}» (${motivo})`).join("; "));
    if (a.idioma_incorrecto) razones.push(`El informe no está en castellano.`);
    if (a.menciona_dolares) razones.push(`Menciona dólares; los importes son euros.`);
    if (d.sin_veredicto > 0 && d.modo === "revisa")
      razones.push(`<b>${d.sin_veredicto} casos quedaron sin veredicto</b> en
        modo revisa: el modelo no se pronunció sobre ellos y conservan la
        decisión del detector.`);
    if (v === "INCOMPLETO" && d.modo === "interpreta")
      razones.push(`En modo <i>interpreta</i> el modelo explica sin decidir, de
        modo que no emite veredictos y la cobertura por veredicto queda
        incompleta <b>por diseño</b>. No indica un fallo.`);

    $("#auditoria").innerHTML = `
      <div class="${clase}">
        <span class="veredicto-aud">${v}</span> según el auditor automático
        · ${d.segundos} s · ${d.modelo} · modo ${d.modo}
        <ul class="auditoria-detalle">${razones.map((r) => `<li>${r}</li>`).join("")}</ul>
      </div>
      <div class="tarjetas">
        ${Object.entries(d.metricas).map(([k, val]) => {
          const grave = k === "n_fraude_descartado" && val > 0;
          return `<div class="tarjeta ${grave ? "grave" : ""}">
            <div class="valor">${val}</div>
            <div class="etiqueta">${ETIQUETAS[k] || k.replace(/_/g, " ")}</div></div>`;
        }).join("")}
      </div>`;
    $("#salida-informe").innerHTML =
      `<h3>Tabla de casos (ensamblada sin modelo)</h3>
       <pre class="mono">${d.tabla}</pre>
       <h3 style="margin-top:24px">Informe redactado</h3>
       <pre class="mono">${d.informe}</pre>`;
  } catch (err) {
    $("#auditoria").innerHTML = `<div class="alerta">${err.message}</div>`;
  }
  this.disabled = false;
  this.textContent = "Ejecutar departamento";
};

comprobarEstado();
