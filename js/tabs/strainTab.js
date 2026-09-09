/**
 * Tab 3: Activities & Strain View Controller
 * Coordinates 24h cumulative strain curve, workout feed cards with HR recovery,
 * and chronic strain debt runway.
 */

import { renderWorkoutFeed } from '../components/workoutCard.js';

export function renderStrainCurve(curveData, currentStrain) {
  const areaPath = document.getElementById("strain-area-path");
  const strokePath = document.getElementById("strain-stroke-path");
  if (!areaPath || !strokePath) return;

  const maxVal = 21.0;
  if (!curveData || curveData.length === 0) {
    if (currentStrain != null && currentStrain > 0) {
      const finalS = currentStrain;
      const points = [];
      const n = 96;
      for (let i = 0; i <= n; i++) {
        const x = (i / n) * 360;
        let s = 0;
        if (i > 30) s = finalS * Math.min(1.0, Math.pow((i - 30) / 45, 1.4));
        const y = 115 - (s / maxVal) * 105;
        points.push({ x, y });
      }
      const pathStr = points.map((p, idx) => `${idx === 0 ? 'M' : 'L'} ${p.x.toFixed(1)},${p.y.toFixed(1)}`).join(' ');
      strokePath.setAttribute("d", pathStr);
      areaPath.setAttribute("d", `${pathStr} L 360,115 L 0,115 Z`);
    } else {
      strokePath.setAttribute("d", "M 0,115 L 360,115");
      areaPath.setAttribute("d", "M 0,115 L 360,115 Z");
    }
    return;
  }

  const n = curveData.length;
  const points = curveData.map((pt, i) => {
    const x = (i / Math.max(1, n - 1)) * 360;
    const s = Math.min(maxVal, Math.max(0, pt.cum_strain || 0));
    const y = 115 - (s / maxVal) * 105;
    return { x, y };
  });

  const pathStr = points.map((p, idx) => `${idx === 0 ? 'M' : 'L'} ${p.x.toFixed(1)},${p.y.toFixed(1)}`).join(' ');
  strokePath.setAttribute("d", pathStr);
  areaPath.setAttribute("d", `${pathStr} L ${points[points.length - 1].x.toFixed(1)},115 L 0,115 Z`);
}

export function renderChronicStrainDebt(v2) {
  const sd = v2 && (v2.chronic_strain_debt || v2.chronic_debt);
  const debtVal = document.getElementById("v2-runway-debt-val");
  const badge = document.getElementById("v2-runway-badge");
  const daysCount = document.getElementById("v2-runway-days-count");
  const barFill = document.getElementById("v2-runway-bar-fill");
  const desc = document.getElementById("v2-runway-desc");

  if (!sd || sd.runway_debt == null) {
    if (debtVal) debtVal.innerText = "--";
    if (daysCount) daysCount.innerText = "-- of 7";
    if (barFill) barFill.style.width = "0%";
    if (desc) desc.innerText = "Awaiting 7-day strain telemetry to compute chronic strain debt.";
    if (badge) {
      badge.className = "px-2.5 py-0.5 rounded-full text-[10px] font-black uppercase tracking-wider bg-zinc-800 text-zinc-400 border border-zinc-700";
      badge.innerText = "AWAITING SYNC";
    }
    return;
  }

  if (debtVal) debtVal.innerText = sd.runway_debt.toFixed(1);
  if (daysCount) daysCount.innerText = `${sd.excess_days_count} of 7`;

  if (barFill) {
    const pct = Math.min(100, Math.round((sd.runway_debt / 6.0) * 100));
    barFill.style.width = `${pct}%`;
  }

  if (badge) {
    if (sd.mandatory_rest_alert || sd.status === "DELOAD_RECOMMENDED") {
      badge.className = "px-2.5 py-0.5 rounded-full text-[10px] font-black uppercase tracking-wider bg-rose-500/10 text-rose-400 border border-rose-500/30";
      badge.innerText = "DELOAD RECOMMENDED";
      if (desc) desc.innerText = "CRITICAL: Chronic strain debt has breached the 6.0 ceiling across 4+ days. Mandatory active recovery or rest day required.";
    } else if (sd.status === "ACCUMULATING") {
      badge.className = "px-2.5 py-0.5 rounded-full text-[10px] font-black uppercase tracking-wider bg-amber-500/10 text-amber-400 border border-amber-500/30";
      badge.innerText = "ACCUMULATING";
      if (desc) desc.innerText = "Chronic strain debt accumulating. Monitor next recovery cycle.";
    } else {
      badge.className = "px-2.5 py-0.5 rounded-full text-[10px] font-black uppercase tracking-wider bg-augur-green/10 text-augur-green border border-augur-green/30";
      badge.innerText = "OPTIMAL RUNWAY";
      if (desc) desc.innerText = "Measures chronic excess load above daily target ceilings. All parameters within safe runway.";
    }
  }
}

export function renderStrainTab(row) {
  if (!row) return;
  const strain = (row.day_strain != null) ? Number(row.day_strain) : (row.strain != null ? Number(row.strain) : 0);
  const v2 = (row.metrics_v2 && typeof row.metrics_v2 === 'object') ? row.metrics_v2 : {};

  const tab3Strain = document.getElementById("tab3-strain-val");
  if (tab3Strain) tab3Strain.innerText = strain.toFixed(1);

  const statusEl = document.getElementById("tab3-strain-status");
  if (statusEl) {
    if (strain >= 16) {
      statusEl.className = "px-2.5 py-0.5 rounded-full text-[10px] font-black uppercase tracking-wider bg-rose-500/10 text-rose-400 border border-rose-500/30 block mt-1";
      statusEl.innerText = "ALL-OUT STIMULUS";
    } else if (strain >= 12) {
      statusEl.className = "px-2.5 py-0.5 rounded-full text-[10px] font-black uppercase tracking-wider bg-augur-green/10 text-augur-green border border-augur-green/30 block mt-1";
      statusEl.innerText = "OPTIMAL OVERLOAD";
    } else if (strain >= 6) {
      statusEl.className = "px-2.5 py-0.5 rounded-full text-[10px] font-black uppercase tracking-wider bg-blue-500/10 text-blue-400 border border-blue-500/30 block mt-1";
      statusEl.innerText = "ACCUMULATING";
    } else {
      statusEl.className = "px-2.5 py-0.5 rounded-full text-[10px] font-black uppercase tracking-wider bg-zinc-800 text-zinc-400 border border-zinc-700 block mt-1";
      statusEl.innerText = "REST / RECOVERY";
    }
  }

  renderStrainCurve(row.strain_curve_15m, strain);
  renderWorkoutFeed(row.activities);
  renderChronicStrainDebt(v2);
}
