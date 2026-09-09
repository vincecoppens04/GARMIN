/**
 * Tab 2: Sleep & Health View Controller
 * Renders sleep prescription, architecture, autonomic dipping profile,
 * HRV trend slope, circadian windows & variance, and interactive sleep simulator.
 */

import { state, getCurrentRecord } from "../state.js";
import { renderVitalsTable } from "../components/vitalsCards.js";

export function renderSleepTab(row) {
  if (!row) return;

  const actualSec = row.sleep_actual_sec;
  const bedSec = row.sleep_bed_sec || actualSec;
  const sleepNeedMin = row.sleep_need_min;
  const currentDebt = row.sleep_debt_min != null ? row.sleep_debt_min : 0;
  const dayStrain = row.day_strain != null ? Number(row.day_strain) : 0;
  const v2 = (row.metrics_v2 && typeof row.metrics_v2 === 'object') ? row.metrics_v2 : {};

  // 1. Target Prescription & Lights-Out Clock
  const tab2Target = document.getElementById("tab2-sleep-target");
  if (tab2Target) {
    if (sleepNeedMin != null) {
      const sH = Math.floor(sleepNeedMin / 60);
      const sM = sleepNeedMin % 60;
      tab2Target.innerText = `${sH}h ${sM.toString().padStart(2, '0')}m`;
    } else {
      tab2Target.innerText = "--h --m";
    }
  }

  const baseNeedMin = (state.settings && state.settings.sleep_need_min) || (row.user_baselines && row.user_baselines.baseline_sleep_need_min) || 435;
  const debtRate = (state.settings && state.settings.debt_payback_pct != null) ? state.settings.debt_payback_pct : 0.33;
  const strainDemand = Math.max(0, Math.floor(Math.max(0, (dayStrain - 10.0) * 4.8)));
  const debtDemand = Math.min(45, Math.max(0, Math.round(currentDebt * debtRate)));

  const tab2Eq = document.getElementById("tab2-sleep-equation");
  if (tab2Eq) {
    tab2Eq.innerText = `${Math.floor(baseNeedMin / 60)}h ${baseNeedMin % 60}m (Base) + ${strainDemand}m (Strain) + ${debtDemand}m (Debt Payback)`;
  }

  const tab2BedClock = document.getElementById("tab2-bedtime-clock");
  if (tab2BedClock) {
    if (row.recommended_bedtime) {
      tab2BedClock.innerText = row.recommended_bedtime;
    } else {
      const wakeTime = (state.settings && state.settings.target_wake_time) || "07:00";
      const [wh, wm] = wakeTime.split(":").map(Number);
      const wakeTotalMin = (wh * 60) + wm;
      const targetMin = sleepNeedMin || baseNeedMin;
      const bedTotalMin = (wakeTotalMin - (targetMin + 15) + 1440) % 1440;
      const bH = Math.floor(bedTotalMin / 60);
      const bM = bedTotalMin % 60;
      tab2BedClock.innerText = `${bH.toString().padStart(2, '0')}:${bM.toString().padStart(2, '0')}`;
    }
  }

  // 2. Sleep Architecture Staging & Efficiency Header
  const tab2SleepDur = document.getElementById("tab2-sleep-dur");
  if (actualSec != null) {
    const actH = Math.floor(actualSec / 3600);
    const actM = Math.floor((actualSec % 3600) / 60);
    if (tab2SleepDur) tab2SleepDur.innerText = `${actH}h ${actM.toString().padStart(2, '0')}m`;
  } else {
    if (tab2SleepDur) tab2SleepDur.innerText = "--h --m";
  }

  const tab2Eff = document.getElementById("tab2-efficiency");
  if (tab2Eff) {
    const effVal = row.sleep_efficiency != null
      ? row.sleep_efficiency
      : (bedSec && actualSec ? Math.min(100, Math.round((actualSec / bedSec) * 100)) : null);
    tab2Eff.innerText = effVal != null ? `${effVal}%` : "--%";
  }

  const tab2Bed = document.getElementById("tab2-bed-dur");
  if (bedSec != null) {
    const bedH = Math.floor(bedSec / 3600);
    const bedM = Math.floor((bedSec % 3600) / 60);
    if (tab2Bed) tab2Bed.innerText = `In Bed: ${bedH}h ${bedM.toString().padStart(2, '0')}m`;
  } else {
    if (tab2Bed) tab2Bed.innerText = "In Bed: --h --m";
  }

  const stageDeep = document.getElementById("stage-deep-val");
  const stageRem = document.getElementById("stage-rem-val");
  const stageLight = document.getElementById("stage-light-val");
  const stageAwake = document.getElementById("stage-awake-val");
  const barDeep = document.getElementById("bar-deep");
  const barRem = document.getElementById("bar-rem");
  const barLight = document.getElementById("bar-light");
  const barAwake = document.getElementById("bar-awake");

  const v2Stages = (v2 && v2.sleep_stages) || (row.metrics_v2 && row.metrics_v2.sleep_stages);
  let deepSec = 0, remSec = 0, lightSec = 0, awakeSec = 0;

  if (v2Stages && (v2Stages.deep_sec > 0 || v2Stages.rem_sec > 0 || v2Stages.light_sec > 0)) {
    deepSec = Number(v2Stages.deep_sec || 0);
    remSec = Number(v2Stages.rem_sec || 0);
    lightSec = Number(v2Stages.light_sec || 0);
    awakeSec = Number(v2Stages.awake_sec || 0);
  } else if (actualSec != null && actualSec > 0) {
    deepSec = Math.round(actualSec * 0.18);
    remSec = Math.round(actualSec * 0.24);
    lightSec = Math.round(actualSec * 0.53);
    awakeSec = Math.max(600, (bedSec || (actualSec + 1260)) - actualSec);
  }

  const totalTrackedSec = deepSec + remSec + lightSec + awakeSec;
  if (totalTrackedSec > 0) {
    const dH = Math.floor(deepSec / 3600), dM = Math.floor((deepSec % 3600) / 60);
    const rH = Math.floor(remSec / 3600), rM = Math.floor((remSec % 3600) / 60);
    const lH = Math.floor(lightSec / 3600), lM = Math.floor((lightSec % 3600) / 60);
    const aM = Math.floor(awakeSec / 60);

    if (stageDeep) stageDeep.innerText = `${dH}h ${dM}m`;
    if (stageRem) stageRem.innerText = `${rH}h ${rM}m`;
    if (stageLight) stageLight.innerText = `${lH}h ${lM}m`;
    if (stageAwake) stageAwake.innerText = `${aM}m`;

    const pctDeep = ((deepSec / totalTrackedSec) * 100).toFixed(1);
    const pctRem = ((remSec / totalTrackedSec) * 100).toFixed(1);
    const pctLight = ((lightSec / totalTrackedSec) * 100).toFixed(1);
    const pctAwake = ((awakeSec / totalTrackedSec) * 100).toFixed(1);

    if (barDeep) barDeep.style.width = pctDeep + "%";
    if (barRem) barRem.style.width = pctRem + "%";
    if (barLight) barLight.style.width = pctLight + "%";
    if (barAwake) barAwake.style.width = pctAwake + "%";
  } else {
    if (stageDeep) stageDeep.innerText = "--h --m";
    if (stageRem) stageRem.innerText = "--h --m";
    if (stageLight) stageLight.innerText = "--h --m";
    if (stageAwake) stageAwake.innerText = "--m";

    if (barDeep) barDeep.style.width = "0%";
    if (barRem) barRem.style.width = "0%";
    if (barLight) barLight.style.width = "0%";
    if (barAwake) barAwake.style.width = "0%";
  }

  // 3. Circadian Consistency & Trailing Variance
  renderCircadianVariance(row);

  // 4. Autonomic Sleep Profile, HRV Trend Slope, Restoration & Restlessness
  renderAutonomicSleepProfile(v2);
  renderHrvTrendSlope(v2);
  renderSleepRestorationAndRestlessness(v2);
  renderCircadianWindows(v2);

  // 5. Sleep Simulator & Vitals Table
  renderSleepSimulator(row);
  renderVitalsTable(row);
}

export function renderCircadianVariance(row) {
  const circScore = row.circadian_consistency;
  const tab2Circ = document.getElementById("tab2-circadian-score");
  const circBadge = document.getElementById("tab2-circadian-badge");

  if (circScore != null) {
    if (tab2Circ) tab2Circ.innerText = circScore + "%";
    if (circBadge) {
      if (circScore >= 75) {
        circBadge.className = "px-2 py-0.5 rounded-full text-[9px] font-black uppercase tracking-wider bg-augur-green/10 text-augur-green border border-augur-green/30";
        circBadge.innerText = "REGULAR";
      } else {
        circBadge.className = "px-2 py-0.5 rounded-full text-[9px] font-black uppercase tracking-wider bg-amber-500/10 text-amber-400 border border-amber-500/30";
        circBadge.innerText = "VARIABLE";
      }
    }
  } else {
    if (tab2Circ) tab2Circ.innerText = "--%";
    if (circBadge) {
      circBadge.className = "px-2 py-0.5 rounded-full text-[9px] font-black uppercase tracking-wider bg-zinc-800 text-zinc-400 border border-zinc-700";
      circBadge.innerText = "NO DATA";
    }
  }

  const tab2CircDev = document.getElementById("tab2-circadian-dev");
  const tab2OnsetVar = document.getElementById("tab2-onset-var");
  const tab2WakeVar = document.getElementById("tab2-wake-var");

  const circWindow = (state.allDailyRecords && state.allDailyRecords.length > 0)
    ? state.allDailyRecords.slice(state.currentDateIndex, state.currentDateIndex + 7)
    : [row];

  const onsetMins = [];
  const wakeMins = [];

  circWindow.forEach(r => {
    if (r.sleep_onset) {
      try {
        const od = new Date(r.sleep_onset);
        if (!isNaN(od.getTime())) {
          const om = (od.getHours() * 60 + od.getMinutes() - 1080 + 1440) % 1440;
          onsetMins.push(om);
        }
      } catch (e) {}
    }
    if (r.sleep_wake) {
      try {
        const wd = new Date(r.sleep_wake);
        if (!isNaN(wd.getTime())) {
          const wm = wd.getHours() * 60 + wd.getMinutes();
          wakeMins.push(wm);
        }
      } catch (e) {}
    }
  });

  function calcStdDev(arr) {
    if (arr.length < 2) return null;
    const avg = arr.reduce((a, b) => a + b, 0) / arr.length;
    const variance = arr.reduce((sum, val) => sum + Math.pow(val - avg, 2), 0) / (arr.length - 1);
    return Math.sqrt(variance);
  }

  const stdOnset = calcStdDev(onsetMins);
  const stdWake = calcStdDev(wakeMins);

  if (stdOnset != null && stdWake != null) {
    const totalDev = Math.round((stdOnset + stdWake) / 2);
    if (tab2CircDev) tab2CircDev.innerText = `±${totalDev}m total variance`;
    if (tab2OnsetVar) tab2OnsetVar.innerText = `±${Math.round(stdOnset)}m variance`;
    if (tab2WakeVar) tab2WakeVar.innerText = `±${Math.round(stdWake)}m variance`;
  } else if (circScore != null) {
    const estOnset = Math.max(10, Math.round(45 * (1 - circScore / 100)));
    const estWake = Math.max(12, Math.round(55 * (1 - circScore / 100)));
    const estTotal = Math.round((estOnset + estWake) / 2);
    if (tab2CircDev) tab2CircDev.innerText = `±${estTotal}m total variance`;
    if (tab2OnsetVar) tab2OnsetVar.innerText = `±${estOnset}m variance`;
    if (tab2WakeVar) tab2WakeVar.innerText = `±${estWake}m variance`;
  } else {
    if (tab2CircDev) tab2CircDev.innerText = "-- total variance";
    if (tab2OnsetVar) tab2OnsetVar.innerText = "-- variance";
    if (tab2WakeVar) tab2WakeVar.innerText = "-- variance";
  }

  if (row.sleep_onset) {
    const onDate = new Date(row.sleep_onset);
    const onStr = onDate.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', hour12: false });
    const tab2Onset = document.getElementById("tab2-onset-time");
    if (tab2Onset) tab2Onset.innerText = onStr;
  } else {
    const tab2Onset = document.getElementById("tab2-onset-time");
    if (tab2Onset) tab2Onset.innerText = "--:--";
  }
  if (row.sleep_wake) {
    const wakeDate = new Date(row.sleep_wake);
    const wakeStr = wakeDate.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', hour12: false });
    const tab2Wake = document.getElementById("tab2-wake-time");
    if (tab2Wake) tab2Wake.innerText = wakeStr;
  } else {
    const tab2Wake = document.getElementById("tab2-wake-time");
    if (tab2Wake) tab2Wake.innerText = "--:--";
  }
}

export function renderAutonomicSleepProfile(v2) {
  const a = v2 && (v2.autonomic_profile || v2.sleep_profile);
  const dipPctEl = document.getElementById("v2-dip-pct");
  const dipTierEl = document.getElementById("v2-dip-tier");
  const badgeEl = document.getElementById("v2-sleep-curve-badge");
  const titleEl = document.getElementById("v2-curve-shape-title");
  const nadirEl = document.getElementById("v2-lowest-hr-text");
  const descEl = document.getElementById("v2-curve-desc");
  const pathEl = document.getElementById("v2-sleep-curve-path");
  const dotEl = document.getElementById("v2-sleep-nadir-dot");

  if (!a || a.dip_pct == null) {
    if (dipPctEl) dipPctEl.innerText = "--%";
    if (dipTierEl) { dipTierEl.innerText = "Awaiting Sync"; dipTierEl.className = "text-[9px] text-zinc-500 font-bold block mt-0.5"; }
    if (badgeEl) {
      badgeEl.className = "px-2.5 py-0.5 rounded-full text-[10px] font-black uppercase tracking-wider bg-zinc-800 text-zinc-400 border border-zinc-700";
      badgeEl.innerText = "AWAITING SYNC";
    }
    if (titleEl) titleEl.innerText = "Curve Profile: Awaiting Sync";
    if (nadirEl) { nadirEl.innerText = "Overnight Nadir: -- bpm"; nadirEl.className = "text-zinc-500 font-bold"; }
    if (descEl) descEl.innerText = "Awaiting overnight telemetry to compute nocturnal autonomic curve.";
    if (pathEl) pathEl.setAttribute("d", "M 0,20 Q 150,20 300,20");
    if (dotEl) { dotEl.setAttribute("cx", "150"); dotEl.setAttribute("cy", "20"); }
    return;
  }

  if (dipPctEl) dipPctEl.innerText = a.dip_pct + "%";
  if (dipTierEl) {
    dipTierEl.innerText = a.dipping_tier + " (" + (a.dip_pct >= 10 ? "10–20%" : "<10%") + ")";
    dipTierEl.className = a.dip_pct >= 10 ? "text-[9px] text-augur-green font-bold block mt-0.5" : "text-[9px] text-amber-400 font-bold block mt-0.5";
  }
  if (nadirEl) {
    nadirEl.innerText = `Overnight Nadir: ${a.lowest_overnight_hr != null ? a.lowest_overnight_hr : '--'} bpm`;
    nadirEl.className = "text-augur-cyan font-bold";
  }
  if (descEl) descEl.innerText = a.curve_desc || "";

  const curve = a.curve_shape || "Hammock";
  if (badgeEl) {
    badgeEl.innerText = `${curve.toUpperCase()} CURVE`;
    if (curve === "Hammock") {
      badgeEl.className = "px-2.5 py-0.5 rounded-full text-[10px] font-black uppercase tracking-wider bg-augur-green/10 text-augur-green border border-augur-green/30";
    } else if (curve === "Slope") {
      badgeEl.className = "px-2.5 py-0.5 rounded-full text-[10px] font-black uppercase tracking-wider bg-amber-500/10 text-amber-400 border border-amber-500/30";
    } else {
      badgeEl.className = "px-2.5 py-0.5 rounded-full text-[10px] font-black uppercase tracking-wider bg-rose-500/10 text-rose-400 border border-rose-500/30";
    }
  }

  if (titleEl) {
    titleEl.innerText = `Curve Profile: ${curve} (${curve === "Hammock" ? "Mid-Sleep Nadir" : (curve === "Slope" ? "Delayed Nadir" : "Plateau")})`;
  }

  if (pathEl && dotEl) {
    if (curve === "Slope") {
      pathEl.setAttribute("d", "M 0,10 Q 180,20 300,34");
      dotEl.setAttribute("cx", "280");
      dotEl.setAttribute("cy", "34");
    } else if (curve === "Plateau") {
      pathEl.setAttribute("d", "M 0,22 Q 150,20 300,21");
      dotEl.setAttribute("cx", "150");
      dotEl.setAttribute("cy", "20");
    } else {
      pathEl.setAttribute("d", "M 0,10 Q 150,34 300,12");
      dotEl.setAttribute("cx", "150");
      dotEl.setAttribute("cy", "34");
    }
  }
}

export function renderHrvTrendSlope(v2) {
  const s = v2 && (v2.hrv_slope || v2.hrv_trend_slope);
  const slopeEl = document.getElementById("v2-hrv-slope");
  const clsEl = document.getElementById("v2-hrv-slope-cls");

  if (!s || s.slope == null) {
    if (slopeEl) { slopeEl.innerText = "--"; slopeEl.className = "text-xl font-black text-zinc-500"; }
    if (clsEl) { clsEl.innerText = "Awaiting Sync"; clsEl.className = "text-[9px] text-zinc-500 font-bold block mt-0.5"; }
    return;
  }

  const sign = s.slope >= 0 ? "+" : "";
  if (slopeEl) slopeEl.innerText = `${sign}${s.slope.toFixed(2)}`;
  if (clsEl) {
    clsEl.innerText = s.classification || "Stable";
    if (s.classification && s.classification.includes("Ascending")) {
      clsEl.className = "text-[9px] text-augur-green font-bold block mt-0.5";
      if (slopeEl) slopeEl.className = "text-xl font-black text-augur-green";
    } else if (s.classification && s.classification.includes("Descending")) {
      clsEl.className = "text-[9px] text-rose-400 font-bold block mt-0.5";
      if (slopeEl) slopeEl.className = "text-xl font-black text-rose-400";
    } else {
      clsEl.className = "text-[9px] text-zinc-400 font-bold block mt-0.5";
      if (slopeEl) slopeEl.className = "text-xl font-black text-white";
    }
  }
}

export function renderSleepRestorationAndRestlessness(v2) {
  const sr = v2 && (v2.sleep_restoration || v2.sleep_restoration_info);
  const pctEl = document.getElementById("v2-restoration-pct");
  const badgeEl = document.getElementById("v2-restoration-badge");
  const idxEl = document.getElementById("v2-restlessness-index");
  const eventsEl = document.getElementById("v2-restless-events");

  if (!sr || sr.restoration_pct == null) {
    if (pctEl) pctEl.innerText = "--%";
    if (idxEl) idxEl.innerText = "--";
    if (eventsEl) eventsEl.innerText = "-- moments";
    if (badgeEl) {
      badgeEl.className = "px-2 py-0.5 rounded-full text-[9px] font-black uppercase bg-zinc-800 text-zinc-400 border border-zinc-700";
      badgeEl.innerText = "AWAITING SYNC";
    }
    return;
  }

  if (pctEl) pctEl.innerText = sr.restoration_pct + "%";
  if (idxEl) idxEl.innerText = sr.restlessness_index != null ? sr.restlessness_index : "--";
  if (eventsEl) eventsEl.innerText = sr.restless_moments != null ? `${sr.restless_moments} moments` : "-- moments";

  if (badgeEl) {
    if (sr.is_optimal) {
      badgeEl.className = "px-2 py-0.5 rounded-full text-[9px] font-black uppercase bg-augur-green/10 text-augur-green border border-augur-green/30";
      badgeEl.innerText = "OPTIMAL";
    } else {
      badgeEl.className = "px-2 py-0.5 rounded-full text-[9px] font-black uppercase bg-amber-500/10 text-amber-400 border border-amber-500/30";
      badgeEl.innerText = "SUBOPTIMAL";
    }
  }
}

export function renderCircadianWindows(v2) {
  const container = document.getElementById("v2-circadian-windows-list");
  if (!container) return;

  const wakeTime = (state.settings && state.settings.target_wake_time) || "07:00";
  const [wh, wm] = wakeTime.split(":").map(Number);
  const wakeTotalMin = (wh * 60) + wm;

  const bedClockEl = document.getElementById("tab2-bedtime-clock");
  let bedH = 23, bedM = 15;
  if (bedClockEl && bedClockEl.innerText && bedClockEl.innerText.includes(":")) {
    const parts = bedClockEl.innerText.split(":").map(Number);
    if (!isNaN(parts[0]) && !isNaN(parts[1])) {
      bedH = parts[0];
      bedM = parts[1];
    }
  }

  const fmtMin = (m) => {
    const norm = ((m % 1440) + 1440) % 1440;
    const h = Math.floor(norm / 60);
    const min = norm % 60;
    return `${h.toString().padStart(2, '0')}:${min.toString().padStart(2, '0')}`;
  };
  const fmtW = (sMin, eMin) => `${fmtMin(wakeTotalMin + sMin)} – ${fmtMin(wakeTotalMin + eMin)}`;

  let bedTotalMin = (bedH * 60) + bedM;
  if (bedTotalMin <= wakeTotalMin) bedTotalMin += 1440;
  const caffCutoffMin = bedTotalMin - 600;
  const caffCutoffStr = fmtMin(caffCutoffMin);

  const windows = [
    {
      id: "cortisol",
      name: "Morning Cortisol & Sunlight Exposure",
      time_window: fmtW(0, 45),
      directive: "Get direct sunlight within 45m of waking to anchor circadian clock.",
      color: "cyan"
    },
    {
      id: "cognitive",
      name: "Peak Cognitive Alertness Window",
      time_window: fmtW(120, 270),
      directive: "Prefrontal cortex alertness optimal. Prime focus for strategic deep work.",
      color: "green"
    },
    {
      id: "physical",
      name: "Peak Strength & VO2 Max Window",
      time_window: fmtW(540, 690),
      directive: "Core body temperature and neuromuscular coordination at physical peak.",
      color: "yellow"
    },
    {
      id: "caffeine",
      name: "Caffeine Clearance Cutoff",
      time_window: caffCutoffStr,
      directive: "Enforces ~10h clearance before lights out to prevent adenosine binding inhibition.",
      color: "rose"
    },
    {
      id: "melatonin",
      name: "Endogenous Melatonin Onset Window",
      time_window: fmtW(840, 900),
      directive: "Dim ambient lights, eliminate blue screens, begin wind-down routine.",
      color: "purple"
    }
  ];

  container.innerHTML = windows.map(w => {
    let colorClass = "text-augur-green bg-augur-green/10 border-augur-green/30";
    if (w.color === "cyan") colorClass = "text-augur-cyan bg-augur-cyan/10 border-augur-cyan/30";
    else if (w.color === "yellow") colorClass = "text-amber-400 bg-amber-500/10 border-amber-500/30";
    else if (w.color === "rose") colorClass = "text-rose-400 bg-rose-500/10 border-rose-500/30";
    else if (w.color === "purple") colorClass = "text-purple-400 bg-purple-500/10 border-purple-500/30";

    return `
      <div class="p-2.5 rounded-2xl bg-augur-cardInner border border-augur-border flex items-start space-x-2.5">
        <div class="px-2 py-1 rounded-xl font-mono text-[10px] font-bold shrink-0 border ${colorClass}">
          ${w.time_window}
        </div>
        <div class="space-y-0.5">
          <span class="text-xs font-bold text-white block leading-tight">${w.name}</span>
          <p class="text-[10px] text-zinc-400 leading-snug font-sans">${w.directive}</p>
        </div>
      </div>
    `;
  }).join('');
}

export function renderSleepSimulator(row) {
  const slider = document.getElementById("v2-sim-slider");
  if (slider) {
    const targetNeed = (row && row.sleep_need_min) ? row.sleep_need_min : 450;
    slider.value = Math.max(300, Math.min(600, targetNeed));
    updateSleepSimulator(slider.value);
  }
}

export function updateSleepSimulator(value) {
  const plannedMin = parseInt(value, 10);
  const h = Math.floor(plannedMin / 60);
  const m = plannedMin % 60;
  const displayEl = document.getElementById("v2-sim-duration-display");
  if (displayEl) displayEl.innerText = `${h}h ${m.toString().padStart(2, '0')}m`;

  const currRec = getCurrentRecord();
  const userBaseline = (state.settings && state.settings.sleep_need_min) || (currRec && currRec.user_baselines && currRec.user_baselines.baseline_sleep_need_min) || 435;
  const currentDebt = (currRec && currRec.sleep_debt_min != null) ? currRec.sleep_debt_min : 0;
  const debtRate = (state.settings && state.settings.debt_payback_pct != null) ? state.settings.debt_payback_pct : 0.33;
  const strain = (currRec && currRec.day_strain != null) ? Number(currRec.day_strain) : 0;
  const strainDemand = Math.max(0, Math.floor(Math.max(0, (strain - 10.0) * 4.8)));
  const debtPaybackDemand = Math.min(45, Math.max(0, Math.round(currentDebt * debtRate)));
  const targetNeed = userBaseline + strainDemand + debtPaybackDemand;

  const decayedDebt = currentDebt * (1.0 - debtRate);
  let newDebt = 0;
  if (plannedMin >= userBaseline) {
    const surplus = plannedMin - userBaseline;
    newDebt = Math.max(0, Math.round(decayedDebt - surplus));
  } else if (plannedMin >= (userBaseline - 30)) {
    newDebt = Math.round(decayedDebt);
  } else {
    const acuteDeficit = (userBaseline - 30) - plannedMin;
    newDebt = Math.min(120, Math.round(decayedDebt + acuteDeficit));
  }

  const sleepRatio = Math.min(1.15, plannedMin / Math.max(1, targetNeed));
  const projectedRec = Math.min(99, Math.max(25, Math.round(sleepRatio * 84)));

  const wakeTime = (state.settings && state.settings.target_wake_time) || (currRec && currRec.user_baselines && currRec.user_baselines.target_wake_time) || "07:00";
  const [wakeH, wakeM] = wakeTime.split(":").map(Number);
  const wakeTotalMin = (wakeH * 60) + wakeM;
  let bedTotalMin = (wakeTotalMin - (plannedMin + 15) + 1440) % 1440;
  const bedH = Math.floor(bedTotalMin / 60);
  const bedM = bedTotalMin % 60;
  const bedStr = `${bedH.toString().padStart(2, '0')}:${bedM.toString().padStart(2, '0')}`;

  const debtRes = document.getElementById("v2-sim-debt-result");
  const recRes = document.getElementById("v2-sim-recovery-result");
  const bedRes = document.getElementById("v2-sim-bedtime-result");

  if (debtRes) {
    debtRes.innerText = `${newDebt}m`;
    debtRes.className = newDebt > 0 ? "text-xs font-black text-amber-400 block mt-0.5" : "text-xs font-black text-augur-green block mt-0.5";
  }
  if (recRes) {
    recRes.innerText = `${projectedRec}%`;
    recRes.className = projectedRec >= 67 ? "text-xs font-black text-augur-green block mt-0.5" : (projectedRec >= 34 ? "text-xs font-black text-amber-400 block mt-0.5" : "text-xs font-black text-rose-400 block mt-0.5");
  }
  if (bedRes) {
    bedRes.innerText = bedStr;
  }
}
