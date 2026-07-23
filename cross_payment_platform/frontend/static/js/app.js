function updateClock() {
  const el = document.getElementById('topbar-clock');
  if (!el) return;
  const now = new Date();
  const opts = { year: 'numeric', month: 'short', day: 'numeric' };
  const dateStr = now.toLocaleDateString('en-US', opts);
  const timeStr = now.toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit' });
  el.textContent = `${dateStr} · ${timeStr}`;
}
updateClock();
setInterval(updateClock, 30000);
