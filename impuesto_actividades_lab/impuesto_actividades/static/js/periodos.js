// Pantalla "Períodos": formulario, detalle del cálculo y tabla histórica.
import {llamar} from "./api.js";
import {leerContexto} from "./contexto.js";
import {$, esc, dinero, numero, mostrarAviso, confirmar} from "./util.js";

let puedeGuardar = false;   // true cuando el cálculo es válido
let ultimoCalculo = null;   // lo que se enviará al guardar

// ---------- Cálculo inmediato (se ejecuta al escribir) ----------
function mostrarDetalleVacio(mensaje, clase = "vacio") {
  $("#detalle").innerHTML = `<h2>Detalle del cálculo</h2><p class="${clase}">${esc(mensaje)}</p>`;
}

function htmlDetalle(calculo, esPorcentaje) {
  const noAplica = "No aplica";
  return `<h2>Detalle del cálculo</h2>
    <dl>
      <dt>Balance</dt><dd>$${dinero(calculo.balance)}</dd>
      <dt>Rango aplicado</dt><dd>$${dinero(calculo.rango_desde)} a $${dinero(calculo.rango_hasta)} (versión ${calculo.tarifa_version})</dd>
      <dt>Precio base</dt><dd>$${dinero(calculo.precio_base)}</dd>
      <dt>Excedente</dt><dd>${esPorcentaje ? noAplica : "$" + dinero(calculo.excedente)}</dd>
      <dt>Bloques de $1,000</dt><dd>${esPorcentaje ? noAplica : numero(calculo.bloques)}</dd>
      <dt>Adicional por bloque</dt><dd>$${dinero(calculo.adicional)}</dd>
      <dt>Porcentaje</dt><dd>${numero(calculo.porcentaje)}</dd>
      <dt>Fórmula</dt><dd>${esc(calculo.formula)}</dd>
    </dl>
    <div class="total"><span>Impuesto mensual</span><b>$${dinero(calculo.precio_mostrado)}</b></div>
    <p class="nota">Subtotal (cantidad × precio): $${dinero(calculo.subtotal)}</p>`;
}

export async function calcularVistaPrevia() {
  puedeGuardar = false;
  $("#guardar").disabled = true;

  const ctx = leerContexto();
  const balance = $("#balance").value.trim();
  if (!ctx.cliente_id || !ctx.producto_codigo || !balance || !$("#desde").value || !$("#hasta").value) {
    return mostrarDetalleVacio("Ingrese cliente, producto, fechas y balance para ver el cálculo.");
  }

  const datos = {...ctx, desde: $("#desde").value, hasta: $("#hasta").value,
                 balance, cantidad: $("#cantidad").value};
  try {
    const r = await llamar("POST", "/api/calcular", datos);
    ultimoCalculo = {datos, calculo: r.calculo};

    let html = htmlDetalle(r.calculo, Number(r.calculo.porcentaje) > 0);
    r.avisos.forEach(a => (html += `<div class="mini warn">${esc(a)}</div>`));
    if (r.conflicto) {
      const lista = r.conflictos.map(c => `${c.desde} a ${c.hasta}`).join("; ");
      const ayuda = $("#cerrar").checked ? "" : " Marque la opción de cierre si el balance cambió.";
      html += `<div class="mini err">${esc(r.conflicto)} (${lista}).${ayuda}</div>`;
    }
    $("#detalle").innerHTML = html;

    puedeGuardar = !r.conflicto || $("#cerrar").checked;
    $("#guardar").disabled = !puedeGuardar;
  } catch (error) {
    mostrarDetalleVacio(error.message, "mini err");
  }
}

// ---------- Guardar ----------
async function guardarPeriodo(evento) {
  evento.preventDefault();
  if (!puedeGuardar) return;

  const {datos, calculo} = ultimoCalculo;
  const acepta = await confirmar("¿Guardar este período?", `
    <dl><dt>Período</dt><dd>${datos.desde} a ${datos.hasta}</dd>
        <dt>Balance</dt><dd>$${dinero(calculo.balance)}</dd>
        <dt>Impuesto mensual</dt><dd><b>$${dinero(calculo.precio_mostrado)}</b></dd></dl>
    <p class="nota">Este precio se conserva y no se recalcula si cambian la tarifa o la fórmula.</p>`);
  if (!acepta) return;

  try {
    const r = await llamar("POST", "/api/periodos", {...datos, cerrar_vigente: $("#cerrar").checked});
    mostrarAviso(r.mensaje, "ok");
    $("#cerrar").checked = false;
    await cargarPeriodos();
    calcularVistaPrevia();
  } catch (error) {
    mostrarAviso(error.message);
  }
}

// ---------- Tabla de períodos ----------
function htmlFila(p) {
  const etiquetaFacturado = p.facturado ? '<span class="tag fact">Facturado</span>' : "";
  return `<tr class="${p.estado === "Vigente" ? "vig" : ""}">
    <td>${p.desde}</td><td>${p.hasta}</td>
    <td class="n">$${dinero(p.balance)}</td><td>${p.producto_codigo}</td>
    <td class="n">$${dinero(p.precio)}</td><td>${esc(p.formula)}</td>
    <td>${p.estado} ${etiquetaFacturado}</td>
    <td><button class="small" data-recalcular="${p.id}" data-facturado="${p.facturado}">Recalcular</button></td>
  </tr>`;
}

export async function cargarPeriodos() {
  const ctx = leerContexto();
  const cuerpo = $("#tabla-periodos tbody");
  if (!ctx.cliente_id) {
    cuerpo.innerHTML = "";
    $("#resumen").innerHTML = `<p class="vacio">Seleccione un cliente para ver sus períodos.</p>`;
    return;
  }

  let ruta = `/api/periodos?cliente_id=${ctx.cliente_id}`;
  if (ctx.producto_codigo) ruta += `&producto_codigo=${ctx.producto_codigo}`;
  const r = await llamar("GET", ruta);

  const vigente = r.impuesto_mensual_vigente.map(v => "$" + dinero(v.precio)).join(" + ") || "Sin período vigente";
  $("#resumen").innerHTML = `
    <div><span>Impuesto mensual vigente</span><b>${vigente}</b></div>
    <div><span>Total referencial de períodos registrados (solo administrativo, no se cobra)</span>
         <b>$${dinero(r.total_referencial)}</b></div>`;

  cuerpo.innerHTML = r.periodos.length
    ? r.periodos.map(htmlFila).join("")
    : `<tr><td colspan="8" class="vacio">Sin períodos registrados. Cree el primero con el formulario.</td></tr>`;
}

// ---------- Recalcular ----------
async function recalcularPeriodo(id, facturado) {
  let motivo = "";
  if (facturado) {
    motivo = prompt("El período ya fue facturado. Indique el motivo de la corrección (requiere usuario autorizador):");
    if (!motivo) return;
  } else {
    const acepta = await confirmar("Recalcular período", "<p>Se aplicarán la tarifa y fórmula vigentes a este período no facturado.</p>");
    if (!acepta) return;
  }
  try {
    const r = await llamar("POST", "/api/periodos/recalcular", {periodo_id: id, usuario: $("#usuario").value, motivo});
    mostrarAviso(r.mensaje, "ok");
    cargarPeriodos();
  } catch (error) {
    mostrarAviso(error.message);
  }
}

// ---------- Eventos de esta pantalla ----------
function sumarUnAnio(fechaTexto) {
  if (!fechaTexto) return "";
  const fecha = new Date(fechaTexto + "T00:00:00Z");
  fecha.setUTCFullYear(fecha.getUTCFullYear() + 1);
  return fecha.toISOString().slice(0, 10);
}

export function iniciarPeriodos() {
  let espera;
  const calcularConRetraso = () => {          // espera 300 ms después de la última tecla
    clearTimeout(espera);
    espera = setTimeout(calcularVistaPrevia, 300);
  };

  $("#form").addEventListener("submit", guardarPeriodo);
  ["#balance", "#cantidad", "#hasta"].forEach(id => $(id).addEventListener("input", calcularConRetraso));
  $("#desde").addEventListener("change", () => {
    $("#hasta").value = sumarUnAnio($("#desde").value);   // por defecto el período dura un año
    calcularConRetraso();
  });
  $("#cerrar").addEventListener("change", calcularVistaPrevia);
  $("#tabla-periodos").addEventListener("click", evento => {
    const boton = evento.target.closest("[data-recalcular]");
    if (boton) recalcularPeriodo(boton.dataset.recalcular, boton.dataset.facturado === "1");
  });
}
