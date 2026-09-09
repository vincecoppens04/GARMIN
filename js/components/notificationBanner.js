/**
 * Sync Freshness Banner & Notification Utilities
 */

export function updateSyncStatusUI(selectedDayOffset, freshness) {
  const syncPulse = document.getElementById("sync-pulse");
  const syncLabel = document.getElementById("last-sync-time");

  if (selectedDayOffset === 0) {
    if (freshness && freshness.is_stale && freshness.last_sync_time) {
      if (syncPulse) syncPulse.className = "w-1.5 h-1.5 rounded-full bg-amber-400";
      if (syncLabel) syncLabel.innerText = `SYNCED ${freshness.last_sync_time}`;
    } else {
      if (syncPulse) syncPulse.className = "w-1.5 h-1.5 rounded-full bg-augur-green";
      if (syncLabel) syncLabel.innerText = "LIVE";
    }
  } else {
    if (syncPulse) syncPulse.className = "w-1.5 h-1.5 rounded-full bg-zinc-500";
    if (syncLabel) syncLabel.innerText = "ARCHIVE";
  }
}

export function showToast(message, type = "info") {
  const toast = document.createElement("div");
  let bg = "bg-zinc-800 border-zinc-700 text-white";
  if (type === "success") bg = "bg-augur-green/10 border-augur-green/30 text-augur-green";
  if (type === "error") bg = "bg-rose-500/10 border-rose-500/30 text-rose-400";
  if (type === "warning") bg = "bg-amber-500/10 border-amber-500/30 text-amber-400";

  toast.className = `fixed top-5 left-1/2 -translate-x-1/2 z-50 px-4 py-2 rounded-2xl border text-xs font-mono shadow-2xl backdrop-blur-xl transition-all duration-300 opacity-0 -translate-y-2 ${bg}`;
  toast.innerText = message;

  document.body.appendChild(toast);
  requestAnimationFrame(() => {
    toast.classList.remove("opacity-0", "-translate-y-2");
    toast.classList.add("opacity-100", "translate-y-0");
  });

  setTimeout(() => {
    toast.classList.add("opacity-0", "-translate-y-2");
    setTimeout(() => toast.remove(), 300);
  }, 2800);
}
