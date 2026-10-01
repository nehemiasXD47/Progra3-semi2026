// Pantalla "Cobro": calcula el cargo de un rango y genera recibos.
import {llamar} from "./api.js";
import {leerContexto} from "./contexto.js";
import {cargarPeriodos} from "./periodos.js";
import {$, esc, dinero, numero, mostrarAviso, ocultarAviso, confirmar} from "./util.js";

let cobroActual = null;

function htmlFila(x) {
  return `<tr><td>${x.desde} a ${x.hasta}</td><td class="n">$${dinero(x.balance)}</td>
    <td class="n">${dinero(x.cantidad)}</td><td class="n">$${dinero(x.precio)}</td>
    <td class="n">${numero(x.meses)}</td><td class="n">$${dinero(x.importe)}</td></tr>`;
}

async function calcularCobro() {
  ocultarAviso();
  const ctx = leerContexto();
  if (!ctx.cliente_id || !ctx.producto_codigo) return mostrarAviso("Seleccione cliente y producto.");

  try {
    const r = await llamar("POST", "/api/cobro", {...ctx, desde: $("#c-desde").value, hasta: $("#c-hasta").value});
    cobroActual = r;

    const filas = r.detalle.map(htmlFila).join("") || `<tr><td colspan="6" class="vacio">Sin períodos en el rango.</td></tr>`;
    let html = `<div class="scroll"><table>
      <thead><tr><th>Período</th><th class="n">Balance</th><th class="n">Cantidad</th>
          <th class="n">Precio mensual</th><th class="n">Meses</th><th class="n">Importe</th></tr></thead>
      <tbody>${filas}</tbody></table></div>
      <div class="total"><span>Total del cobro</span><b>$${dinero(r.total)}</b></div>`;
    r.avisos.forEach(a => (html += `<div class="mini warn">${esc(a)}</div>`));
    if (r.detalle.length) html += `<p><button class="primary" id="c-generar" type="button">Generar recibo</button></p>`;
    $("#c-res").innerHTML = html;
  } catch (error) {
    mostrarAviso(error.message);
  }
}

async function generarRecibo() {
  const acepta = await confirmar("¿Generar recibo?", `<p>Total: <b>$${dinero(cobroActual.total)}</b>.
    Los períodos incluidos quedarán marcados como facturados y no podrán recalcularse automáticamente.</p>`);
  if (!acepta) return;

  try {
    const ctx = leerContexto();
    const r = await llamar("POST", "/api/recibos", {...ctx, desde: $("#c-desde").value, hasta: $("#c-hasta").value});
    mostrarAviso(r.mensaje, "ok");
    $("#c-res").innerHTML = "";
    cargarRecibos();
    cargarPeriodos();
  } catch (error) {
    mostrarAviso(error.message);
  }
}

export async function cargarRecibos() {
  const r = await llamar("GET", "/api/recibos");
  $("#tabla-recibos tbody").innerHTML = r.filas.map(f => `<tr>
      <td>${f.id}</td><td>${esc(f.cliente)}</td><td>${f.producto_codigo}</td>
      <td>${f.desde}</td><td>${f.hasta}</td><td class="n">$${dinero(f.total)}</td><td>${esc(f.creado_por)}</td></tr>`).join("")
    || `<tr><td colspan="7" class="vacio">Aún no hay recibos.</td></tr>`;
}

export function iniciarCobro() {
  $("#c-calc").addEventListener("click", calcularCobro);
  $("#c-res").addEventListener("click", e => e.target.id === "c-generar" && generarRecibo());
}
