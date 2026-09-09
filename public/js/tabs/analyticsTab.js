/**
 * Tab 5: Analytics & Engine Health View Controller
 * Coordinates ACWR, Training Monotony, Cardiovascular Polarization (80/20),
 * Daytime Stress Balance, and 5 continuous multi-range stacked graphs.
 */

import { state } from '../state.js';
import {
  drawSvgLine,
  drawSvgBars,
  formatDateShort,
  activeScrubberData,
  setupChartScrubbers
} from '../charts.js';

export function renderAcwrGauge(v2) {
  const a = v2 && (v2.acwr || v2.acwr_info);
  const valEl = document.getElementById("v2-acwr-val");
  const badge = document.getElementById("v2-acwr-badge");
  const loads = document.getElementById("v2-acwr-loads");
  const needle = document.getElementById("v2-acwr-needle");

  if (!a || a.acwr == null) {
    if (valEl) { valEl.innerText = "--"; valEl.className = "text-3xl font-black font-mono text-zinc-500"; }
    if (loads) loads.innerText = "Acute: -- | Chronic: --";
    if (needle) needle.style.left = "0%";
    if (badge) {
      badge.className = "px-2.5 py-0.5 rounded-full text-[10px] font-black uppercase tracking-wider bg-zinc-800 text-zinc-400 border border-zinc-700";
      badge.innerText = "AWAITING SYNC";
    }
    return;
  }

  if (valEl) {
    valEl.innerText = a.acwr.toFixed(2);
    valEl.className = a.zone_key === "SWEET_SPOT" ? "text-3xl font-black font-mono text-augur-green" : (a.zone_key === "DANGER" ? "text-3xl font-black font-mono text-rose-400" : "text-3xl font-black font-mono text-amber-400");
  }
  if (loads) loads.innerText = `Acute: ${a.acute_load} | Chronic: ${a.chronic_load}`;

  if (needle) {
    needle.style.left = `${Math.min(95, Math.max(5, (a.acwr / 2.0) * 100))}%`;
  }

  if (badge) {
    if (a.zone_key === "SWEET_SPOT") {
      badge.className = "px-2.5 py-0.5 rounded-full text-[10px] font-black uppercase tracking-wider bg-augur-green/10 text-augur-green border border-augur-green/30";
      badge.innerText = "SWEET SPOT";
    } else if (a.zone_key === "UNDER") {
      badge.className = "px-2.5 py-0.5 rounded-full text-[10px] font-black uppercase tracking-wider bg-cyan-500/10 text-cyan-400 border border-cyan-500/30";
      badge.innerText = "UNDERTRAINING";
    } else if (a.zone_key === "OVERLOAD") {
      badge.className = "px-2.5 py-0.5 rounded-full text-[10px] font-black uppercase tracking-wider bg-amber-500/10 text-amber-400 border border-amber-500/30";
      badge.innerText = "OVERLOAD";
    } else {
      badge.className = "px-2.5 py-0.5 rounded-full text-[10px] font-black uppercase tracking-wider bg-rose-500/10 text-rose-400 border border-rose-500/30";
      badge.innerText = "DANGER ZONE";
    }
  }
}

export function renderTrainingMonotony(v2) {
  const m = v2 && (v2.training_monotony || v2.monotony_info);
  const badge = document.getElementById("v2-monotony-badge");
  const valEl = document.getElementById("v2-monotony-val");
  const strainIdxEl = document.getElementById("v2-monotony-strain-idx");

  if (!m || m.training_monotony == null) {
    if (valEl) valEl.innerText = "--";
    if (strainIdxEl) strainIdxEl.innerText = "--";
    if (badge) {
      badge.className = "px-2 py-0.5 rounded-full text-[9px] font-black uppercase bg-zinc-800 text-zinc-400 border border-zinc-700";
      badge.innerText = "AWAITING SYNC";
    }
    return;
  }

  if (valEl) valEl.innerText = m.training_monotony.toFixed(2);
  if (strainIdxEl) strainIdxEl.innerText = m.strain_index.toFixed(1);

  if (badge) {
    if (m.is_monotonous) {
      badge.className = "px-2 py-0.5 rounded-full text-[9px] font-black uppercase bg-rose-500/10 text-rose-400 border border-rose-500/30";
      badge.innerText = "MONOTONOUS";
    } else {
      badge.className = "px-2 py-0.5 rounded-full text-[9px] font-black uppercase bg-augur-green/10 text-augur-green border border-augur-green/30";
      badge.innerText = "BALANCED";
    }
  }
}

export function renderCardiovascularPolarization(v2, row) {
  const badge = document.getElementById("v2-polar-badge");
  const barLow = document.getElementById("v2-polar-bar-low");
  const barMod = document.getElementById("v2-polar-bar-mod");
  const barHigh = document.getElementById("v2-polar-bar-high");
  const pctLow = document.getElementById("v2-polar-pct-low");
  const pctMod = document.getElementById("v2-polar-pct-mod");
  const pctHigh = document.getElementById("v2-polar-pct-high");

  const currentRow = row || state.cachedTelemetry || {};
  const acts = currentRow.activities || [];
  const dayStrain = currentRow.day_strain != null ? Number(currentRow.day_strain) : (currentRow.strain != null ? Number(currentRow.strain) : 0);

  let lowMin = 0, modMin = 0, highMin = 0;

  // 1. Check if the active day has activities with exact HR zones
  let dayHasZoneData = false;
  acts.forEach(act => {
    const z1 = Number(act.hrTimeInZone_1 || 0);
    const z2 = Number(act.hrTimeInZone_2 || 0);
    const z3 = Number(act.hrTimeInZone_3 || 0);
    const z4 = Number(act.hrTimeInZone_4 || 0);
    const z5 = Number(act.hrTimeInZone_5 || 0);
    if ((z1 + z2 + z3 + z4 + z5) > 0) {
      lowMin += (z1 + z2) / 60.0;
      modMin += z3 / 60.0;
      highMin += (z4 + z5) / 60.0;
      dayHasZoneData = true;
    }
  });

  // 2. If no single-day zone data, compute rolling 7-day window anchored at currentDateIndex
  if (!dayHasZoneData) {
    const window7d = (state.allDailyRecords && state.allDailyRecords.length > 0)
      ? state.allDailyRecords.slice(state.currentDateIndex, state.currentDateIndex + 7)
      : [currentRow];

    let windowHasZoneData = false;
    window7d.forEach(d => {
      const dActs = d.activities || [];
      dActs.forEach(act => {
        const z1 = Number(act.hrTimeInZone_1 || 0);
        const z2 = Number(act.hrTimeInZone_2 || 0);
        const z3 = Number(act.hrTimeInZone_3 || 0);
        const z4 = Number(act.hrTimeInZone_4 || 0);
        const z5 = Number(act.hrTimeInZone_5 || 0);
        if ((z1 + z2 + z3 + z4 + z5) > 0) {
          lowMin += (z1 + z2) / 60.0;
          modMin += z3 / 60.0;
          highMin += (z4 + z5) / 60.0;
          windowHasZoneData = true;
        }
      });
    });

    // 3. If still no direct zone minutes, synthesize from daily strain distributions
    if (!windowHasZoneData) {
      if (acts.length === 0 && dayStrain < 6.0) {
        lowMin = 100;
        modMin = 0;
        highMin = 0;
      } else {
        window7d.forEach(d => {
          const s = Number(d.day_strain || d.strain || 0);
          if (s < 8.0) {
            lowMin += 60;
          } else if (s <= 13.0) {
            lowMin += 45;
            modMin += (s - 7.0) * 4;
          } else {
            lowMin += 40;
            modMin += 15;
            highMin += (s - 12.0) * 6;
          }
        });
      }
    }
  }

  const totalMin = lowMin + modMin + highMin;
  let pLow = 80, pMod = 10, pHigh = 10;
  let isRestDay = (acts.length === 0 && dayStrain < 6.0 && (!lowMin || (modMin === 0 && highMin === 0)));

  if (totalMin > 0) {
    pLow = Math.round((lowMin / totalMin) * 100);
    pMod = Math.round((modMin / totalMin) * 100);
    pHigh = Math.max(0, 100 - pLow - pMod);
  } else if (v2 && v2.load_polarization && v2.load_polarization.pct_low != null) {
    pLow = v2.load_polarization.pct_low;
    pMod = v2.load_polarization.pct_mod;
    pHigh = v2.load_polarization.pct_high;
  }

  if (barLow) barLow.style.width = `${pLow}%`;
  if (barMod) barMod.style.width = `${pMod}%`;
  if (barHigh) barHigh.style.width = `${pHigh}%`;

  if (pctLow) pctLow.innerText = `${pLow}% (≥80%)`;
  if (pctMod) pctMod.innerText = `${pMod}% (≤10%)`;
  if (pctHigh) pctHigh.innerText = `${pHigh}% (~10%)`;

  if (badge) {
    if (isRestDay || pLow >= 95) {
      badge.className = "px-2.5 py-0.5 rounded-full text-[10px] font-black uppercase tracking-wider bg-augur-green/10 text-augur-green border border-augur-green/30";
      badge.innerText = "REST / EASY DAY";
    } else if (pLow >= 75 && pMod <= 12) {
      badge.className = "px-2.5 py-0.5 rounded-full text-[10px] font-black uppercase tracking-wider bg-augur-green/10 text-augur-green border border-augur-green/30";
      badge.innerText = "POLARIZED (80/20)";
    } else if (pMod > 12) {
      badge.className = "px-2.5 py-0.5 rounded-full text-[10px] font-black uppercase tracking-wider bg-amber-500/10 text-amber-400 border border-amber-500/30";
      badge.innerText = "THRESHOLD HEAVY";
    } else {
      badge.className = "px-2.5 py-0.5 rounded-full text-[10px] font-black uppercase tracking-wider bg-rose-500/10 text-rose-400 border border-rose-500/30";
      badge.innerText = "ANAEROBIC HEAVY";
    }
  }
}

export function renderDaytimeStressBalance(v2) {
  const sb = v2 && (v2.daytime_stress_balance || v2.stress_balance);
  const badge = document.getElementById("v2-stress-balance-badge");
  const ratioEl = document.getElementById("v2-stress-ratio-val");
  const restEl = document.getElementById("v2-stress-rest-min");
  const highEl = document.getElementById("v2-stress-high-min");

  if (!sb || sb.stress_balance_ratio == null) {
    if (ratioEl) { ratioEl.innerText = "--"; ratioEl.className = "text-2xl font-black text-zinc-500"; }
    if (restEl) restEl.innerText = "-- min Rest (<25)";
    if (highEl) highEl.innerText = "-- min Stress (≥50)";
    if (badge) {
      badge.className = "px-2 py-0.5 rounded-full text-[9px] font-black uppercase bg-zinc-800 text-zinc-400 border border-zinc-700";
      badge.innerText = "AWAITING SYNC";
    }
    return;
  }

  if (ratioEl) {
    ratioEl.innerText = sb.stress_balance_ratio.toFixed(2);
    ratioEl.className = sb.is_optimal ? "text-2xl font-black text-augur-green" : "text-2xl font-black text-amber-400";
  }
  if (restEl) restEl.innerText = `${sb.rest_minutes} min Rest (<25)`;
  if (highEl) highEl.innerText = `${sb.high_stress_minutes} min Stress (≥50)`;

  if (badge) {
    if (sb.is_optimal) {
      badge.className = "px-2 py-0.5 rounded-full text-[9px] font-black uppercase bg-augur-green/10 text-augur-green border border-augur-green/30";
      badge.innerText = "OPTIMAL BALANCE";
    } else {
      badge.className = "px-2 py-0.5 rounded-full text-[9px] font-black uppercase bg-amber-500/10 text-amber-400 border border-amber-500/30";
      badge.innerText = "SYMPATHETIC OVERDRIVE";
    }
  }
}

export function getHistoryForRange(range) {
  const source = (state.allDailyRecords && Array.isArray(state.allDailyRecords) && state.allDailyRecords.length > 0)
    ? state.allDailyRecords
    : (state.cachedTelemetry && state.cachedTelemetry.history_records && state.cachedTelemetry.history_records.length > 0
      ? state.cachedTelemetry.history_records
      : (state.cachedTelemetry ? [state.cachedTelemetry] : []));
  return source.slice(0, range);
}

export function setGlobalTimeRange(days) {
  state.currentRangeDays = days;

  // Update button visual state in both Tab 4 and Tab 5
  [7, 30, 90].forEach(d => {
    ['tab4-range-', 'tab5-range-'].forEach(prefix => {
      const btn = document.getElementById(prefix + d);
      if (btn) {
        if (d === days) {
          btn.className = "px-2.5 py-1 rounded-lg bg-augur-green text-black font-bold transition-all shadow-sm";
        } else {
          btn.className = "px-2.5 py-1 rounded-lg text-zinc-400 hover:text-white transition-all";
        }
      }
    });
  });

  // Update Tab 4 Header & Subtitles
  const habitTitle = document.getElementById("habit-engine-title");
  if (habitTitle) habitTitle.innerText = `Habit Correlation Engine (Past ${days} Days)`;

  const sampleSub = document.getElementById("habit-sample-window");
  if (sampleSub) sampleSub.innerText = `Sample window: ${days} days`;

  const dataSlice = getHistoryForRange(days);

  // Recompute Tab 4 Strain vs Recovery Balance for this exact window
  const balanceTitle = document.getElementById("balance-quadrant-title");
  const sEl = document.getElementById("balance-7d-strain");
  const rEl = document.getElementById("balance-7d-recovery");
  const dot = document.getElementById("quadrant-user-dot");

  if (dataSlice.length === 0) {
    if (balanceTitle) balanceTitle.innerText = `Awaiting Sync (${days}d Avg)`;
    if (sEl) sEl.innerText = "--";
    if (rEl) rEl.innerText = "--";
    if (dot) dot.style.display = "none";
  } else {
    const validStrain = dataSlice.filter(r => r.day_strain != null);
    const validRec = dataSlice.filter(r => r.recovery_score != null);
    const avgStrain = validStrain.length ? validStrain.reduce((acc, r) => acc + Number(r.day_strain), 0) / validStrain.length : null;
    const avgRec = validRec.length ? validRec.reduce((acc, r) => acc + Number(r.recovery_score), 0) / validRec.length : null;

    if (balanceTitle) balanceTitle.innerText = `Optimal Overload (${days}d Avg)`;
    if (sEl) sEl.innerText = avgStrain != null ? avgStrain.toFixed(1) : "--";
    if (rEl) rEl.innerText = avgRec != null ? Math.round(avgRec) + "%" : "--";

    if (dot) {
      if (avgStrain != null && avgRec != null) {
        dot.style.display = "block";
        const xPct = Math.min(92, Math.max(8, (avgStrain / 21.0) * 100));
        const yPct = Math.min(92, Math.max(8, 100 - avgRec));
        dot.style.left = xPct + "%";
        dot.style.top = yPct + "%";
      } else {
        dot.style.display = "none";
      }
    }
  }

  renderAnalyticsGraphs(dataSlice, days);
}

export function renderAnalyticsGraphs(records, days) {
  const dCount = days || state.currentRangeDays || 7;
  const data = records || getHistoryForRange(dCount);
  const chronological = [...data].reverse();
  const n = chronological.length;

  if (!n) {
    const paths = ["hrv-trend-path", "rhr-trend-path", "resp-trend-path", "spo2-trend-path"];
    paths.forEach(id => {
      const el = document.getElementById(id);
      if (el) el.setAttribute("d", "");
    });
    const groups = ["sleep-bars-group", "strain-bars-group"];
    groups.forEach(id => {
      const el = document.getElementById(id);
      if (el) el.innerHTML = "";
    });
    const hrvReadout = document.getElementById("analytics-hrv-readout");
    if (hrvReadout) hrvReadout.innerText = `Latest: -- ms | ${dCount}d Mean: -- ms`;
    const rhrReadout = document.getElementById("analytics-rhr-readout");
    if (rhrReadout) rhrReadout.innerText = `Latest: -- bpm | ${dCount}d Mean: -- bpm | Floor: -- bpm`;
    const sleepReadout = document.getElementById("analytics-sleep-readout");
    const baseNeedMin = state.settings.sleep_need_min || 435;
    const baseNeedStr = `${Math.floor(baseNeedMin / 60)}h ${baseNeedMin % 60}m`;
    if (sleepReadout) sleepReadout.innerText = `Avg: --h --m / Need: ${baseNeedStr}`;
    const strainReadout = document.getElementById("analytics-strain-readout");
    if (strainReadout) strainReadout.innerText = `${dCount}d Avg Strain: -- / 21.0`;
    const vReadout = document.getElementById("analytics-vitals-readout");
    if (vReadout) vReadout.innerText = `RPM: -- br/min | SpO2: --%`;
    return;
  }

  const hrvPoints = chronological.filter(d => d.hrv_rmssd != null);
  const rhrPoints = chronological.filter(d => d.rhr != null);
  const strainPoints = chronological.filter(d => d.day_strain != null);
  const sleepPoints = chronological.filter(d => d.sleep_actual_sec != null);
  const respPoints = chronological.filter(d => d.resp_rate != null);
  const spo2Points = chronological.filter(d => d.spo2 != null);

  activeScrubberData.hrv = hrvPoints.map(d => ({ date: formatDateShort(d.date), val: d.hrv_rmssd }));
  activeScrubberData.rhr = rhrPoints.map(d => ({ date: formatDateShort(d.date), val: d.rhr }));
  activeScrubberData.sleep = sleepPoints.map(d => ({ date: formatDateShort(d.date), val: d.sleep_actual_sec / 3600 }));
  activeScrubberData.strain = strainPoints.map(d => ({ date: formatDateShort(d.date), val: Number(d.day_strain) }));
  activeScrubberData.resp = respPoints.map(d => ({ date: formatDateShort(d.date), val: d.resp_rate }));
  activeScrubberData.spo2 = spo2Points.map(d => ({ date: formatDateShort(d.date), val: d.spo2 }));
  setupChartScrubbers();

  // 1. HRV
  const hrvVals = hrvPoints.map(d => d.hrv_rmssd);
  const hrvReadout = document.getElementById("analytics-hrv-readout");
  if (hrvVals.length) {
    const avgHrv = Math.round(hrvVals.reduce((a, b) => a + b, 0) / hrvVals.length);
    const latestHrv = hrvVals[hrvVals.length - 1];
    if (hrvReadout) hrvReadout.innerText = `Latest: ${latestHrv} ms | ${dCount}d Mean: ${avgHrv} ms`;
    drawSvgLine("hrv-trend-path", hrvVals, 50, 120);
  } else {
    if (hrvReadout) hrvReadout.innerText = `Latest: -- ms | ${dCount}d Mean: -- ms`;
    const path = document.getElementById("hrv-trend-path");
    if (path) path.setAttribute("d", "");
  }

  // 2. RHR
  const rhrVals = rhrPoints.map(d => d.rhr);
  const rhrReadout = document.getElementById("analytics-rhr-readout");
  if (rhrVals.length) {
    const floorRhr = Math.min(...rhrVals);
    const avgRhr = Math.round(rhrVals.reduce((a, b) => a + b, 0) / rhrVals.length);
    const latestRhr = rhrVals[rhrVals.length - 1];
    if (rhrReadout) rhrReadout.innerText = `Latest: ${latestRhr} bpm | ${dCount}d Mean: ${avgRhr} bpm | Floor: ${floorRhr} bpm`;
    drawSvgLine("rhr-trend-path", rhrVals, 38, 56);
  } else {
    if (rhrReadout) rhrReadout.innerText = `Latest: -- bpm | ${dCount}d Mean: -- bpm | Floor: -- bpm`;
    const path = document.getElementById("rhr-trend-path");
    if (path) path.setAttribute("d", "");
  }

  // 3. Sleep
  const sleepVals = sleepPoints.map(d => d.sleep_actual_sec / 3600);
  const baseNeedMin = state.settings.sleep_need_min || 435;
  const baseNeedStr = `${Math.floor(baseNeedMin / 60)}h ${baseNeedMin % 60}m`;
  const sleepReadout = document.getElementById("analytics-sleep-readout");
  if (sleepVals.length) {
    const avgSleep = sleepVals.reduce((a, b) => a + b, 0) / sleepVals.length;
    const sH = Math.floor(avgSleep);
    const sM = Math.round((avgSleep - sH) * 60);
    if (sleepReadout) sleepReadout.innerText = `Avg: ${sH}h ${sM}m / Need: ${baseNeedStr}`;
    drawSvgBars("sleep-bars-group", sleepVals, 9.5, val => val < (baseNeedMin / 60) ? "#FFB800" : "#00F0FF");
  } else {
    if (sleepReadout) sleepReadout.innerText = `Avg: --h --m / Need: ${baseNeedStr}`;
    const grp = document.getElementById("sleep-bars-group");
    if (grp) grp.innerHTML = "";
  }

  // 4. Strain
  const strainVals = strainPoints.map(d => Number(d.day_strain));
  const strainReadout = document.getElementById("analytics-strain-readout");
  if (strainVals.length) {
    const avgStrain = (strainVals.reduce((a, b) => a + b, 0) / strainVals.length).toFixed(1);
    if (strainReadout) strainReadout.innerText = `${dCount}d Avg Strain: ${avgStrain} / 21.0`;
    drawSvgBars("strain-bars-group", strainVals, 21.0, val => val > 16.0 ? '#FF3B30' : (val > 12.0 ? '#00E599' : '#3B82F6'));
  } else {
    if (strainReadout) strainReadout.innerText = `${dCount}d Avg Strain: -- / 21.0`;
    const grp = document.getElementById("strain-bars-group");
    if (grp) grp.innerHTML = "";
  }

  // 5. Respiration & SpO2
  const respVals = respPoints.map(d => d.resp_rate);
  const spo2Vals = spo2Points.map(d => d.spo2);
  if (respVals.length) drawSvgLine("resp-trend-path", respVals, 10, 16);
  else { const p = document.getElementById("resp-trend-path"); if (p) p.setAttribute("d", ""); }
  if (spo2Vals.length) drawSvgLine("spo2-trend-path", spo2Vals, 92, 100);
  else { const p = document.getElementById("spo2-trend-path"); if (p) p.setAttribute("d", ""); }
  const rLatest = respVals.length ? respVals[respVals.length - 1] : null;
  const sLatest = spo2Vals.length ? spo2Vals[spo2Vals.length - 1] : null;
  const vReadout = document.getElementById("analytics-vitals-readout");
  if (vReadout) {
    const rStr = rLatest != null ? `${rLatest.toFixed(1)} br/min` : "-- br/min";
    const sStr = sLatest != null ? `${Math.round(sLatest)}%` : "--%";
    vReadout.innerText = `RPM: ${rStr} | SpO2: ${sStr}`;
  }
}

export function renderAnalyticsTab(row) {
  if (!row) return;
  const v2 = (row.metrics_v2 && typeof row.metrics_v2 === 'object') ? row.metrics_v2 : {};

  renderAcwrGauge(v2);
  renderTrainingMonotony(v2);
  renderCardiovascularPolarization(v2, row);
  renderDaytimeStressBalance(v2);
  setGlobalTimeRange(state.currentRangeDays || 30);
}
