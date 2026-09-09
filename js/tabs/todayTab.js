/**
 * Tab 1: Today View Controller
 * Renders the command center: Recovery Hero Ring, Vitals Pills, Strain vs Target Bracket,
 * Workout Prescriber, AI Morning Briefing, and Pre-Symptomatic Immune Severity Index.
 */

import { renderRecoveryRing } from "../components/recoveryRing.js";

export function renderTodayTab(row) {
  if (!row) return;

  const rec = row.recovery_score != null ? Number(row.recovery_score) : (row.recovery != null ? Number(row.recovery) : null);
  const strain = row.day_strain != null ? Number(row.day_strain) : (row.strain != null ? Number(row.strain) : null);
  const tMin = row.target_strain_min != null ? Number(row.target_strain_min) : null;
  const tMax = row.target_strain_max != null ? Number(row.target_strain_max) : null;
  const driver = row.recovery_driver || "Awaiting sync";
  const hrv = row.hrv_rmssd != null ? Math.round(row.hrv_rmssd) : null;
  const rhr = row.rhr != null ? Math.round(row.rhr) : null;
  const briefing = row.ai_briefing || "";
  const actualSec = row.sleep_actual_sec;
  const sleepNeedMin = row.sleep_need_min;
  const debtMin = row.sleep_debt_min;

  // 1. Hero Ring & Recovery Driver
  renderRecoveryRing(rec);
  const driverEl = document.getElementById("recovery-driver");
  if (driverEl) driverEl.innerText = driver;

  const hrvEl = document.getElementById("hrv-val");
  const rhrEl = document.getElementById("rhr-val");
  if (hrvEl) hrvEl.innerText = hrv != null ? (hrv + " ms") : "-- ms";
  if (rhrEl) rhrEl.innerText = rhr != null ? (rhr + " bpm") : "-- bpm";

  // 2. Cardiovascular Strain vs Target Bracket
  const strainEl = document.getElementById("strain-val");
  const tMinEl = document.getElementById("target-strain-min");
  const tMaxEl = document.getElementById("target-strain-max");
  if (strainEl) strainEl.innerText = strain != null ? strain.toFixed(1) : "--";
  if (tMinEl) tMinEl.innerText = tMin != null ? tMin.toFixed(1) : "--";
  if (tMaxEl) tMaxEl.innerText = tMax != null ? tMax.toFixed(1) : "--";

  const fillPct = strain != null ? Math.min(100, Math.max(0, (strain / 21.0) * 100)) : 0;
  const fillEl = document.getElementById("strain-bar-fill");
  if (fillEl) fillEl.style.width = fillPct + "%";

  if (tMin != null && tMax != null) {
    const bracketLeft = Math.min(100, Math.max(0, (tMin / 21.0) * 100));
    const bracketWidth = Math.min(100 - bracketLeft, Math.max(2, ((tMax - tMin) / 21.0) * 100));
    const bracketEl = document.getElementById("strain-target-bracket");
    if (bracketEl) {
      bracketEl.style.left = bracketLeft + "%";
      bracketEl.style.width = bracketWidth + "%";
    }
  }

  // 3. Sleep & Debt Snapshot
  const sleepActEl = document.getElementById("sleep-actual-val");
  if (sleepActEl) {
    if (actualSec != null) {
      const actH = Math.floor(actualSec / 3600);
      const actM = Math.floor((actualSec % 3600) / 60);
      sleepActEl.innerText = `${actH}h ${actM.toString().padStart(2, '0')}m`;
    } else {
      sleepActEl.innerText = "--h --m";
    }
  }

  const sleepNeedEl = document.getElementById("sleep-need-val");
  if (sleepNeedEl) {
    if (sleepNeedMin != null) {
      const needH = Math.floor(sleepNeedMin / 60);
      const needM = sleepNeedMin % 60;
      sleepNeedEl.innerText = `${needH}h ${needM.toString().padStart(2, '0')}m`;
    } else {
      sleepNeedEl.innerText = "--h --m";
    }
  }

  const debtEl = document.getElementById("debt-pill");
  if (debtEl) {
    if (debtMin != null) {
      if (debtMin > 0) {
        debtEl.className = "inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-bold font-mono bg-amber-500/10 text-amber-400 border border-amber-500/30 mt-0.5";
        debtEl.innerText = `+${debtMin}m`;
      } else {
        debtEl.className = "inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-bold font-mono bg-augur-green/10 text-augur-green border border-augur-green/30 mt-0.5";
        debtEl.innerText = "0m";
      }
    } else {
      debtEl.className = "inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-bold font-mono bg-zinc-800 text-zinc-400 border border-zinc-700 mt-0.5";
      debtEl.innerText = "--m";
    }
  }

  // 4. Health Monitor Status Card
  const healthStatus = row.health_status || "NORMAL";
  const healthIcon = document.getElementById("health-flag-icon");
  const healthTitle = document.getElementById("health-flag-title");
  const healthSub = document.getElementById("health-flag-sub");

  if (healthStatus === "NORMAL") {
    if (healthIcon) {
      healthIcon.className = "w-6 h-6 rounded-lg bg-augur-green/10 border border-augur-green/30 flex items-center justify-center text-augur-green";
      healthIcon.innerHTML = '<svg class="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2.5" d="M5 13l4 4L19 7" /></svg>';
    }
    if (healthTitle) healthTitle.innerText = "All Vitals Normal";
    if (healthSub) healthSub.innerText = "HRV, RHR, SpO2 & Respiration within baseline";
  } else {
    if (healthIcon) {
      healthIcon.className = "w-6 h-6 rounded-lg bg-amber-500/10 border border-amber-500/30 flex items-center justify-center text-amber-400";
      healthIcon.innerHTML = '<svg class="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2.5" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" /></svg>';
    }
    if (healthTitle) healthTitle.innerText = "Metric Outlier Detected";
    if (healthSub) healthSub.innerText = (row.health_alerts && row.health_alerts.length > 0) ? row.health_alerts.join(", ") : "Autonomic deviation observed";
  }

  // 5. AI Briefing
  const briefingEl = document.getElementById("ai-briefing-text");
  if (briefingEl) {
    briefingEl.innerText = briefing ? `"${briefing}"` : "Awaiting morning sync for autonomic synthesis.";
  }

  // 6. V2 Components: Workout Prescriber & Immune Strain Index
  const v2 = (row.metrics_v2 && typeof row.metrics_v2 === 'object') ? row.metrics_v2 : {};
  renderWorkoutPrescriber(v2, rec);
  renderImmuneStrainIndex(v2, row);

  // 7. Habit Logging Banner
  checkHabitBannerStatus(row.date);
}

export function renderWorkoutPrescriber(v2, rec) {
  const p = v2 && v2.workout_prescriber;
  const zoneBadge = document.getElementById("v2-prescriber-zone");
  const cadenceEl = document.getElementById("v2-prescriber-cadence");
  const dirEl = document.getElementById("v2-prescriber-directive");
  const focusEl = document.getElementById("v2-prescriber-focus");
  const modEl = document.getElementById("v2-prescriber-modalities");

  if (!p || !p.zone) {
    if (zoneBadge) {
      zoneBadge.className = "px-2.5 py-0.5 rounded-full text-[10px] font-black uppercase tracking-wider bg-zinc-800 text-zinc-400 border border-zinc-700";
      zoneBadge.innerText = "AWAITING SYNC";
    }
    if (cadenceEl) { cadenceEl.innerText = "AWAITING READINESS"; cadenceEl.className = "text-[9px] font-mono text-zinc-500 font-bold"; }
    if (dirEl) dirEl.innerText = "Awaiting recovery data to prescribe workout stimulus.";
    if (focusEl) focusEl.innerText = "--";
    if (modEl) modEl.innerHTML = `<span class="px-2.5 py-1 rounded-xl text-[10px] font-mono bg-augur-cardInner border border-augur-border text-zinc-500">--</span>`;
    return;
  }

  if (dirEl) dirEl.innerText = p.directive || "--";
  if (focusEl) focusEl.innerText = p.focus || "--";

  if (zoneBadge) {
    if (p.zone === "GREEN") {
      zoneBadge.className = "px-2.5 py-0.5 rounded-full text-[10px] font-black uppercase tracking-wider bg-augur-green/10 text-augur-green border border-augur-green/30";
      zoneBadge.innerText = "GREEN ZONE";
      if (cadenceEl) { cadenceEl.innerText = "POWER & HIGH CNS LOAD"; cadenceEl.className = "text-[9px] font-mono text-augur-green font-bold"; }
    } else if (p.zone === "YELLOW") {
      zoneBadge.className = "px-2.5 py-0.5 rounded-full text-[10px] font-black uppercase tracking-wider bg-amber-500/10 text-amber-400 border border-amber-500/30";
      zoneBadge.innerText = "YELLOW ZONE";
      if (cadenceEl) { cadenceEl.innerText = "AEROBIC BASE (<LT1)"; cadenceEl.className = "text-[9px] font-mono text-amber-400 font-bold"; }
    } else {
      zoneBadge.className = "px-2.5 py-0.5 rounded-full text-[10px] font-black uppercase tracking-wider bg-rose-500/10 text-rose-400 border border-rose-500/30";
      zoneBadge.innerText = "RED ZONE";
      if (cadenceEl) { cadenceEl.innerText = "ACTIVE RECOVERY / FLOW"; cadenceEl.className = "text-[9px] font-mono text-rose-400 font-bold"; }
    }
  }

  if (modEl && p.modalities && p.modalities.length > 0) {
    modEl.innerHTML = p.modalities.map(m => `
      <span class="px-2.5 py-1 rounded-xl text-[10px] font-mono bg-augur-cardInner border border-augur-border text-zinc-200">${m}</span>
    `).join('');
  } else if (modEl) {
    modEl.innerHTML = `<span class="px-2.5 py-1 rounded-xl text-[10px] font-mono bg-augur-cardInner border border-augur-border text-zinc-500">--</span>`;
  }
}

export function renderImmuneStrainIndex(v2, row) {
  const im = v2 && (v2.immune_strain || v2.immune_info);
  const scoreEl = document.getElementById("v2-immune-score-val");
  const tierBadge = document.getElementById("v2-immune-tier-badge");
  const envelopeEl = document.getElementById("v2-immune-envelope-text");
  const needleEl = document.getElementById("v2-immune-needle");
  const descEl = document.getElementById("v2-immune-desc");
  const zResp = document.getElementById("v2-z-resp");
  const zRhr = document.getElementById("v2-z-rhr");
  const zHrv = document.getElementById("v2-z-hrv");
  const zSpo2 = document.getElementById("v2-z-spo2");

  if (!im || im.immune_strain_index == null) {
    if (scoreEl) { scoreEl.innerText = "--"; scoreEl.className = "text-3xl font-black font-mono text-zinc-500 leading-none"; }
    if (tierBadge) {
      tierBadge.className = "px-2.5 py-0.5 rounded-full text-[10px] font-black uppercase tracking-wider bg-zinc-800 text-zinc-400 border border-zinc-700";
      tierBadge.innerText = "AWAITING SYNC";
    }
    if (envelopeEl) envelopeEl.innerText = "--";
    if (descEl) descEl.innerText = "Immune surveillance awaiting telemetry data.";
    if (needleEl) needleEl.style.left = "0%";
    if (zResp) zResp.innerText = "--";
    if (zRhr) zRhr.innerText = "--";
    if (zHrv) zHrv.innerText = "--";
    if (zSpo2) zSpo2.innerText = "--";
    return;
  }

  const score = im.immune_strain_index;
  if (scoreEl) scoreEl.innerText = score;

  if (needleEl) {
    needleEl.style.left = `${Math.min(96, Math.max(4, score))}%`;
  }

  if (tierBadge) {
    if (score >= 56) {
      tierBadge.className = "px-2.5 py-0.5 rounded-full text-[10px] font-black uppercase tracking-wider bg-rose-500/10 text-rose-400 border border-rose-500/30";
      tierBadge.innerText = "INFECTION RISK";
      if (scoreEl) scoreEl.className = "text-3xl font-black font-mono text-rose-400 leading-none";
      if (envelopeEl) envelopeEl.innerText = "High Risk (56–100)";
      if (descEl) descEl.innerText = "CRITICAL: Multiple vital deviations suggest systemic infection or severe autonomic exhaustion.";
    } else if (score >= 26) {
      tierBadge.className = "px-2.5 py-0.5 rounded-full text-[10px] font-black uppercase tracking-wider bg-amber-500/10 text-amber-400 border border-amber-500/30";
      tierBadge.innerText = "WATCH";
      if (scoreEl) scoreEl.className = "text-3xl font-black font-mono text-amber-400 leading-none";
      if (envelopeEl) envelopeEl.innerText = "Watch (26–55)";
      if (descEl) descEl.innerText = "WATCH: Elevated physiological strain observed. Restrict heavy glycolytic efforts.";
    } else {
      tierBadge.className = "px-2.5 py-0.5 rounded-full text-[10px] font-black uppercase tracking-wider bg-augur-green/10 text-augur-green border border-augur-green/30";
      tierBadge.innerText = "NORMAL";
      if (scoreEl) scoreEl.className = "text-3xl font-black font-mono text-augur-green leading-none";
      if (envelopeEl) envelopeEl.innerText = "Baseline (0–25)";
      if (descEl) descEl.innerText = "Immune surveillance active across 4 physiological vectors. All autonomic markers within healthy baseline envelopes.";
    }
  }

  const zs = im.z_scores || {};
  if (zResp) zResp.innerText = zs.resp != null ? `${zs.resp >= 0 ? '+' : ''}${zs.resp}σ` : "--";
  if (zRhr) zRhr.innerText = zs.rhr != null ? `${zs.rhr >= 0 ? '+' : ''}${zs.rhr}σ` : "--";
  if (zHrv) zHrv.innerText = zs.hrv != null ? `${zs.hrv >= 0 ? '+' : ''}${zs.hrv}σ` : "--";
  if (zSpo2) zSpo2.innerText = zs.spo2 != null ? `${zs.spo2 >= 0 ? '+' : ''}${zs.spo2}σ` : "--";
}

export function checkHabitBannerStatus(dateStr) {
  const banner = document.getElementById("habit-logging-banner");
  if (!banner) return;
  const loggedDates = JSON.parse(localStorage.getItem("augur_logged_habits") || "[]");
  if (loggedDates.includes(dateStr)) {
    banner.style.display = "none";
  } else {
    banner.style.display = "flex";
  }
}
