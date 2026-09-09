/**
 * Vitals Cards & Diagnostic Modal Component
 * Renders 4-vital status pills (HRV, RHR, Respiration, SpO2) and clinical envelope diagnostics.
 */

import { state, getCurrentRecord } from "../state.js";
import { renderStatusPill } from "./recoveryRing.js";

export function renderVitalsTable(row) {
  if (!row) return;

  if (row.vitals_baseline) {
    const vb = row.vitals_baseline;
    if (vb.hrv_rmssd) {
      document.getElementById("row-hrv-val").innerText = vb.hrv_rmssd.val + " ms";
      document.getElementById("row-hrv-base").innerText = `${vb.hrv_rmssd.baseline_min}–${vb.hrv_rmssd.baseline_max} ms`;
      renderStatusPill("row-hrv-status", vb.hrv_rmssd.status);
    } else {
      document.getElementById("row-hrv-val").innerText = row.hrv_rmssd != null ? row.hrv_rmssd + " ms" : "-- ms";
      document.getElementById("row-hrv-base").innerText = "--";
      renderStatusPill("row-hrv-status", "--");
    }
    if (vb.rhr) {
      document.getElementById("row-rhr-val").innerText = vb.rhr.val + " bpm";
      document.getElementById("row-rhr-base").innerText = `${vb.rhr.baseline_min}–${vb.rhr.baseline_max} bpm`;
      renderStatusPill("row-rhr-status", vb.rhr.status);
    } else {
      document.getElementById("row-rhr-val").innerText = row.rhr != null ? row.rhr + " bpm" : "-- bpm";
      document.getElementById("row-rhr-base").innerText = "--";
      renderStatusPill("row-rhr-status", "--");
    }
    if (vb.resp_rate) {
      document.getElementById("row-resp-val").innerText = vb.resp_rate.val.toFixed(1) + " brpm";
      document.getElementById("row-resp-base").innerText = `${vb.resp_rate.baseline_min}–${vb.resp_rate.baseline_max} brpm`;
      renderStatusPill("row-resp-status", vb.resp_rate.status);
    } else {
      document.getElementById("row-resp-val").innerText = row.resp_rate != null ? Number(row.resp_rate).toFixed(1) + " brpm" : "-- brpm";
      document.getElementById("row-resp-base").innerText = "--";
      renderStatusPill("row-resp-status", "--");
    }
    if (vb.spo2) {
      document.getElementById("row-spo2-val").innerText = vb.spo2.val + "%";
      document.getElementById("row-spo2-base").innerText = `${vb.spo2.baseline_min}–${vb.spo2.baseline_max}%`;
      renderStatusPill("row-spo2-status", vb.spo2.status);
    } else {
      document.getElementById("row-spo2-val").innerText = row.spo2 != null ? row.spo2 + "%" : "--%";
      document.getElementById("row-spo2-base").innerText = "--";
      renderStatusPill("row-spo2-status", "--");
    }
  } else {
    document.getElementById("row-hrv-val").innerText = row.hrv_rmssd != null ? row.hrv_rmssd + " ms" : "-- ms";
    document.getElementById("row-hrv-base").innerText = "--";
    renderStatusPill("row-hrv-status", row.hrv_rmssd != null ? "OK" : "--");

    document.getElementById("row-rhr-val").innerText = row.rhr != null ? row.rhr + " bpm" : "-- bpm";
    document.getElementById("row-rhr-base").innerText = "--";
    renderStatusPill("row-rhr-status", row.rhr != null ? "OK" : "--");

    document.getElementById("row-resp-val").innerText = row.resp_rate != null ? Number(row.resp_rate).toFixed(1) + " brpm" : "-- brpm";
    document.getElementById("row-resp-base").innerText = "--";
    renderStatusPill("row-resp-status", row.resp_rate != null ? "OK" : "--");

    document.getElementById("row-spo2-val").innerText = row.spo2 != null ? row.spo2 + "%" : "--%";
    document.getElementById("row-spo2-base").innerText = "--";
    renderStatusPill("row-spo2-status", row.spo2 != null ? "OK" : "--");
  }
}

export function openVitalsModal() {
  const modal = document.getElementById("vitals-modal");
  if (!modal) return;

  const record = getCurrentRecord();
  if (record) {
    if (record.date) {
      const parts = record.date.split("-");
      if (parts.length >= 3) {
        const d = new Date(Number(parts[0]), Number(parts[1]) - 1, Number(parts[2]));
        const dateStr = d.toLocaleDateString('en-US', { weekday: 'short', month: 'short', day: 'numeric' });
        const dateEl = document.getElementById("vitals-modal-date");
        if (dateEl) dateEl.innerText = `${dateStr} • Trailing 30-day statistical envelope (μ ± 1.5σ)`;
      }
    }

    const hrvVal = record.hrv_rmssd ? Math.round(record.hrv_rmssd) : 94;
    const rhrVal = record.rhr ? Math.round(record.rhr) : 45;
    const respVal = record.resp_rate ? Number(record.resp_rate).toFixed(1) : "12.0";
    const spo2Val = record.spo2 ? Math.round(record.spo2) : 97;

    const setTxt = (id, txt) => { const el = document.getElementById(id); if (el) el.innerText = txt; };
    setTxt("vitals-val-hrv", hrvVal);
    setTxt("vitals-val-rhr", rhrVal);
    setTxt("vitals-val-resp", respVal);
    setTxt("vitals-val-spo2", spo2Val);

    const alerts = record.health_alerts || [];
    const banner = document.getElementById("vitals-modal-banner");

    if (alerts && alerts.length > 0) {
      if (banner) {
        banner.className = "p-3.5 rounded-2xl bg-amber-500/10 border border-amber-500/30 space-y-1";
        banner.innerHTML = `
          <div class="flex items-center justify-between">
            <span class="text-[10px] font-black font-mono tracking-widest text-amber-400 uppercase flex items-center gap-1.5">
              <span class="w-1.5 h-1.5 rounded-full bg-amber-400 animate-ping"></span>
              Autonomic Anomaly Flagged
            </span>
            <span class="text-[9px] font-mono text-amber-400 font-bold">[ATTENTION]</span>
          </div>
          <p class="text-[11px] text-zinc-300 font-sans leading-relaxed">
            ${alerts.join(". ")}. Autonomic tone shows deviation from your 30-day baseline. Prioritize restorative recovery.
          </p>
        `;
      }
    } else {
      if (banner) {
        banner.className = "p-3.5 rounded-2xl bg-augur-green/10 border border-augur-green/30 space-y-1";
        banner.innerHTML = `
          <div class="flex items-center justify-between">
            <span class="text-[10px] font-black font-mono tracking-widest text-augur-green uppercase flex items-center gap-1.5">
              <span class="w-1.5 h-1.5 rounded-full bg-augur-green"></span>
              All Vitals Nominal
            </span>
            <span class="text-[9px] font-mono text-augur-green font-bold">[OK]</span>
          </div>
          <p class="text-[11px] text-zinc-300 font-sans leading-relaxed">
            Overnight autonomic vitals are resting peacefully inside your rolling 30-day biological equilibrium window.
          </p>
        `;
      }
    }
  }

  modal.classList.remove("hidden");
}

export function closeVitalsModal() {
  const modal = document.getElementById("vitals-modal");
  if (modal) modal.classList.add("hidden");
}
