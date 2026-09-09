/**
 * Circular Recovery Gauge & Status Pill Renderers
 */

export const CIRCUMFERENCE = 452.39;

export function renderRecoveryRing(score) {
  const circle = document.getElementById("recovery-circle-bar");
  const badge = document.getElementById("recovery-badge");
  const valEl = document.getElementById("recovery-val");

  if (score == null) {
    if (valEl) valEl.innerText = "--";
    if (circle) {
      circle.style.strokeDashoffset = CIRCUMFERENCE;
      circle.style.stroke = "#52525b";
    }
    if (badge) {
      badge.className = "px-2.5 py-0.5 rounded-full text-[10px] font-black uppercase tracking-wider bg-zinc-800 text-zinc-400 border border-zinc-700";
      badge.innerText = "AWAITING SYNC";
    }
    return;
  }

  if (valEl) valEl.innerText = Math.round(score);
  const s = Math.max(0, Math.min(100, score));
  const offset = CIRCUMFERENCE - (s / 100) * CIRCUMFERENCE;
  if (circle) circle.style.strokeDashoffset = offset;

  if (s >= 67) {
    if (circle) circle.style.stroke = "#00E599";
    if (badge) {
      badge.className = "px-2.5 py-0.5 rounded-full text-[10px] font-black uppercase tracking-wider bg-augur-green/10 text-augur-green border border-augur-green/30";
      badge.innerText = "OPTIMAL";
    }
  } else if (s >= 34) {
    if (circle) circle.style.stroke = "#FFB800";
    if (badge) {
      badge.className = "px-2.5 py-0.5 rounded-full text-[10px] font-black uppercase tracking-wider bg-amber-500/10 text-amber-400 border border-amber-500/30";
      badge.innerText = "ADEQUATE";
    }
  } else {
    if (circle) circle.style.stroke = "#FF3B30";
    if (badge) {
      badge.className = "px-2.5 py-0.5 rounded-full text-[10px] font-black uppercase tracking-wider bg-red-500/10 text-red-400 border border-red-500/30";
      badge.innerText = "RESTORATIVE";
    }
  }
}

export function renderStatusPill(elementId, status) {
  const el = document.getElementById(elementId);
  if (!el) return;
  if (status === "OK") {
    el.className = "px-2 py-0.5 rounded-full text-[10px] font-black uppercase bg-augur-green/10 text-augur-green border border-augur-green/30";
    el.innerText = "[OK]";
  } else if (status === "OUTLIER") {
    el.className = "px-2 py-0.5 rounded-full text-[10px] font-black uppercase bg-amber-500/10 text-amber-400 border border-amber-500/30";
    el.innerText = "[!]";
  } else {
    el.className = "px-2 py-0.5 rounded-full text-[10px] font-black uppercase bg-zinc-800 text-zinc-500 border border-zinc-700";
    el.innerText = "--";
  }
}
