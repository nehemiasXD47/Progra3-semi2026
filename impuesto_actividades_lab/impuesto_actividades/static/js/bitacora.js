// Pantalla "Bitácora": últimos eventos de auditoría.
import {llamar} from "./api.js";
import {$, esc} from "./util.js";

export async function cargarBitacora() {
  const r = await llamar("GET", "/api/bitacora");
  $("#tabla-bitacora tbody").innerHTML = r.filas.map(f => `<tr>
      <td>${esc(f.fecha.slice(0, 19))}</td><td>${esc(f.usuario)}</td><td>${esc(f.accion)}</td>
      <td>${f.periodo_id ?? ""}</td><td style="white-space:normal;max-width:520px">${esc(f.detalle)}</td></tr>`).join("");
}
