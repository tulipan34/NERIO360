// Fecha mínima local (sin desfases por zona horaria).
const today = new Date();
const localDate = [today.getFullYear(), String(today.getMonth()+1).padStart(2,'0'), String(today.getDate()).padStart(2,'0')].join('-');
document.querySelectorAll('input[type="date"]').forEach(el => { el.min = localDate; });
