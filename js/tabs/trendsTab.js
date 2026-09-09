/**
 * Tab 4: Trends & Insights View Controller
 * Coordinates Alcohol latency, Caffeine clearance simulator,
 * Strain vs. Recovery balance 4-quadrant scatter plot,
 * Cardiovascular Biological Age, and Habit correlation engine.
 */

import { state } from '../state.js';

let userCaffeineCups = parseInt(localStorage.getItem('augur_caff_cups') || '2', 10);
let userCaffeineHour = localStorage.getItem('augur_caff_hour') || '14:00';

export function renderAlcoholClearance(v2) {
  const a = v2 && (v2.alcohol_clearance || v2.alcohol_latency);
  const badge = document.getElementById("v2-alcohol-badge");
  const latEl = document.getElementById("v2-alcohol-latency");
  const deltaEl = document.getElementById("v2-alcohol-delta");
  const descEl = document.getElementById("v2-alcohol-desc");

  const hadAlcohol = a && a.had_alcohol;
  if (!hadAlcohol) {
    const lat = (a && a.latency_hr != null) ? a.latency_hr : 1.2;
    if (latEl) latEl.innerText = `${lat}h`;
    if (deltaEl) { deltaEl.innerText = "+0.0h"; deltaEl.className = "text-xl font-black text-augur-green block mt-0.5"; }
    if (descEl) descEl.innerText = "Zero alcohol detected. Autonomic nervous system stabilized within normal physiological latency (~1.2h) with zero sympathetic penalty.";
    if (badge) {
      badge.className = "px-2.5 py-0.5 rounded-full text-[10px] font-black uppercase tracking-wider bg-augur-green/10 text-augur-green border border-augur-green/30";
      badge.innerText = "CLEAN BASELINE";
    }
    return;
  }

  const lat = a.latency_hr != null ? a.latency_hr : 4.5;
  const delta = a.delta_latency_hr != null ? a.delta_latency_hr : 3.0;

  if (latEl) latEl.innerText = `${lat}h`;
  if (deltaEl) {
    deltaEl.innerText = `+${delta}h`;
    deltaEl.className = "text-xl font-black text-amber-400 block mt-0.5";
  }

  if (badge) {
    if (delta > 1.0) {
      badge.className = "px-2.5 py-0.5 rounded-full text-[10px] font-black uppercase tracking-wider bg-amber-500/10 text-amber-400 border border-amber-500/30";
      badge.innerText = "SYMPATHETIC DELAY";
      if (descEl) descEl.innerText = `Alcohol intake delayed nocturnal cardiovascular stabilization by ${delta} hours past baseline.`;
    } else {
      badge.className = "px-2.5 py-0.5 rounded-full text-[10px] font-black uppercase tracking-wider bg-augur-green/10 text-augur-green border border-augur-green/30";
      badge.innerText = "CLEAN BASELINE";
      if (descEl) descEl.innerText = "Nocturnal heart rate reached stable baseline within expected physiological latency window.";
    }
  }
}

export function adjustCaffeineCups(delta) {
  userCaffeineCups = Math.max(0, Math.min(6, userCaffeineCups + delta));
  localStorage.setItem('augur_caff_cups', userCaffeineCups);
  updateCaffeineSimulator();
}

export function onCaffeineHourChanged(val) {
  userCaffeineHour = val;
  localStorage.setItem('augur_caff_hour', userCaffeineHour);
  updateCaffeineSimulator();
}

export function updateCaffeineSimulator(targetRow) {
  const row = targetRow || state.cachedTelemetry || {};
  const cupsValEl = document.getElementById("caff-cups-val");
  const mgDisplay = document.getElementById("caff-mg-display");
  const hourSelect = document.getElementById("caff-hour-select");
  const initEl = document.getElementById("v2-caff-initial");
  const timeEl = document.getElementById("v2-caff-time");
  const bedEl = document.getElementById("v2-caff-bedtime");
  const badge = document.getElementById("v2-caffeine-badge");
  const pathEl = document.getElementById("v2-caff-curve-path");
  const dotEl = document.getElementById("v2-caff-bedtime-dot");
  const adviceEl = document.getElementById("v2-caff-advice");

  if (cupsValEl) cupsValEl.innerText = `${userCaffeineCups} ${userCaffeineCups === 1 ? 'cup' : 'cups'}`;
  if (hourSelect) hourSelect.value = userCaffeineHour;

  const mgPerCup = 95;
  const initialMg = userCaffeineCups * mgPerCup;
  if (mgDisplay) mgDisplay.innerText = `${initialMg} mg total`;
  if (initEl) initEl.innerText = `${initialMg} mg`;
  if (timeEl) timeEl.innerText = userCaffeineCups > 0 ? userCaffeineHour : "None";

  if (initialMg === 0) {
    if (bedEl) { bedEl.innerText = "0.0 mg"; bedEl.className = "text-sm font-black text-augur-green block mt-0.5"; }
    if (badge) {
      badge.className = "px-2.5 py-0.5 rounded-full text-[10px] font-black uppercase tracking-wider bg-zinc-800 text-zinc-400 border border-zinc-700";
      badge.innerText = "NO CAFFEINE";
    }
    if (pathEl) pathEl.setAttribute("d", "M 0,45 L 300,45");
    if (dotEl) { dotEl.setAttribute("cx", "295"); dotEl.setAttribute("cy", "45"); dotEl.setAttribute("fill", "#00E599"); }
    if (adviceEl) adviceEl.innerText = "Adenosine receptors unblocked. Natural homeostatic sleep pressure will accumulate optimally.";
    return;
  }

  // Compute elapsed hours to bedtime
  let bedHour = 23, bedMin = 15;
  if (row.sleep_onset) {
    try {
      const od = new Date(row.sleep_onset);
      if (!isNaN(od.getTime())) {
        bedHour = od.getHours();
        bedMin = od.getMinutes();
      }
    } catch (e) {}
  } else {
    const bedClockEl = document.getElementById("tab2-bedtime-clock");
    if (bedClockEl && bedClockEl.innerText && bedClockEl.innerText.includes(":")) {
      const parts = bedClockEl.innerText.split(":").map(Number);
      if (!isNaN(parts[0]) && !isNaN(parts[1])) {
        bedHour = parts[0];
        bedMin = parts[1];
      }
    } else if (row.recommended_bedtime) {
      const parts = row.recommended_bedtime.split(":").map(Number);
      if (!isNaN(parts[0]) && !isNaN(parts[1])) {
        bedHour = parts[0];
        bedMin = parts[1];
      }
    }
  }

  const [inpH, inpM] = userCaffeineHour.split(':').map(Number);
  let elapsedMin = (bedHour * 60 + bedMin) - (inpH * 60 + inpM);
  if (elapsedMin < 0) elapsedMin += 1440;
  const elapsedHr = Math.max(1.0, elapsedMin / 60.0);

  // Exponential decay: N(t) = N0 * 0.5^(t / half_life)
  const halfLife = 5.0;
  const remainingMg = initialMg * Math.pow(0.5, elapsedHr / halfLife);
  const roundedRemaining = Math.round(remainingMg * 10) / 10;

  if (bedEl) {
    bedEl.innerText = `${roundedRemaining.toFixed(1)} mg`;
    bedEl.className = roundedRemaining > 25.0 ? "text-sm font-black text-rose-400 block mt-0.5" : "text-sm font-black text-augur-green block mt-0.5";
  }

  if (badge) {
    if (roundedRemaining > 25.0) {
      badge.className = "px-2.5 py-0.5 rounded-full text-[10px] font-black uppercase tracking-wider bg-rose-500/10 text-rose-400 border border-rose-500/30";
      badge.innerText = "SLEEP DISRUPTION (>25mg)";
    } else {
      badge.className = "px-2.5 py-0.5 rounded-full text-[10px] font-black uppercase tracking-wider bg-augur-green/10 text-augur-green border border-augur-green/30";
      badge.innerText = "BEDTIME CLEAR (≤25mg)";
    }
  }

  // Redraw SVG exponential decay path
  const maxMgPlot = Math.max(300, initialMg * 1.1);
  const mgToY = (mg) => 45 - Math.min(40, (mg / maxMgPlot) * 40);

  const points = [];
  const steps = 30;
  for (let s = 0; s <= steps; s++) {
    const x = (s / steps) * 295;
    const curT = (s / steps) * elapsedHr;
    const curMg = initialMg * Math.pow(0.5, curT / halfLife);
    const y = mgToY(curMg);
    points.push({ x, y });
  }

  if (pathEl) {
    const dStr = points.map((p, i) => `${i === 0 ? 'M' : 'L'} ${p.x.toFixed(1)},${p.y.toFixed(1)}`).join(' ');
    pathEl.setAttribute("d", dStr);
    pathEl.setAttribute("stroke", roundedRemaining > 25.0 ? "#F43F5E" : "#FFB800");
  }

  if (dotEl) {
    const lastP = points[points.length - 1];
    dotEl.setAttribute("cx", lastP.x.toFixed(1));
    dotEl.setAttribute("cy", lastP.y.toFixed(1));
    dotEl.setAttribute("fill", roundedRemaining > 25.0 ? "#F43F5E" : "#00E599");
  }

  if (adviceEl) {
    if (roundedRemaining > 25.0) {
      const cutOffTimeH = Math.floor(Math.max(7, bedHour - (5.0 * Math.log2(initialMg / 25.0))));
      adviceEl.innerHTML = `⚠️ <strong class="text-rose-400 font-bold">${roundedRemaining.toFixed(1)}mg remains at bedtime</strong> (${elapsedHr.toFixed(1)}h later). To avoid deep sleep fragmentation, move your last cup earlier to before <span class="text-white font-mono">${String(cutOffTimeH).padStart(2, '0')}:00</span>.`;
    } else {
      adviceEl.innerHTML = `✓ Safe clearance. Only <strong class="text-augur-green font-bold">${roundedRemaining.toFixed(1)}mg remains at bedtime</strong> (${elapsedHr.toFixed(1)}h clearance window). Deep slow-wave architecture protected.`;
    }
  }
}

export function renderCaffeineClearance(v2, row) {
  const targetRow = (row && (row.sleep_onset || row.recommended_bedtime || row.date))
    ? row
    : (v2 && (v2.sleep_onset || v2.recommended_bedtime || v2.date) ? v2 : state.cachedTelemetry) || {};
  updateCaffeineSimulator(targetRow);
}

export function renderHabitCorrelations(correlations) {
  const container = document.getElementById("habit-correlation-list");
  if (!container) return;

  if (!correlations || correlations.length === 0) {
    container.innerHTML = `
      <div class="p-3.5 rounded-2xl bg-augur-cardInner border border-augur-border space-y-2.5">
        <div class="flex items-center justify-between">
          <span class="text-[10px] font-mono text-zinc-400 font-bold uppercase tracking-wider">Reference Impact Benchmarks</span>
          <button onclick="openHabitModal()" class="px-2.5 py-1 rounded-xl bg-purple-500/20 text-purple-300 hover:bg-purple-500/30 border border-purple-500/40 text-[9px] font-mono font-bold transition-all flex items-center gap-1">
            <span>+ Log Habits</span>
          </button>
        </div>
        <div class="space-y-1.5 text-[10px] font-mono">
          <div class="flex justify-between items-center py-1 border-b border-augur-border/40">
            <span class="text-zinc-300"> Alcohol / Night Out</span>
            <span class="text-rose-400 font-bold">-14% Rec | -12 ms HRV</span>
          </div>
          <div class="flex justify-between items-center py-1 border-b border-augur-border/40">
            <span class="text-zinc-300"> Late Meal (&lt;2h bed)</span>
            <span class="text-amber-400 font-bold">-8% Rec | +4 bpm RHR</span>
          </div>
          <div class="flex justify-between items-center py-1 border-b border-augur-border/40">
            <span class="text-zinc-300"> Late Caffeine (&gt;15:00)</span>
            <span class="text-amber-400 font-bold">-6% Rec | -15m Deep</span>
          </div>
          <div class="flex justify-between items-center py-1">
            <span class="text-zinc-300"> Screen in Bed</span>
            <span class="text-zinc-400 font-bold">-4% Rec | +8m Latency</span>
          </div>
        </div>
        <p class="text-[9px] text-zinc-500 leading-snug">Personalized correlations unlock after logging 3+ entries with recovery data.</p>
      </div>
    `;
    return;
  }

  container.innerHTML = correlations.map(item => {
    const hrvText = item.delta_hrv < 0 ? `HRV: ${item.delta_hrv} ms` : `HRV: +${item.delta_hrv} ms`;
    const rhrText = item.delta_rhr > 0 ? `RHR: +${item.delta_rhr} bpm` : `RHR: ${item.delta_rhr} bpm`;
    const recText = item.delta_rec ? `Recovery: ${item.delta_rec}%` : (item.delta_deep ? `Deep Sleep: ${item.delta_deep}m` : rhrText);

    return `
      <div class="p-3 rounded-2xl bg-augur-cardInner border border-augur-border flex items-center justify-between">
        <div class="space-y-0.5">
          <div class="flex items-center space-x-1.5">
            <span class="w-1.5 h-1.5 rounded-full bg-amber-400"></span>
            <span class="text-xs font-bold text-zinc-200">${item.label}</span>
            <span class="text-[9px] text-zinc-500 font-normal">(${item.count}x)</span>
          </div>
          <div class="text-[10px] text-zinc-400 flex items-center space-x-2">
            <span class="text-rose-400 font-semibold">${recText}</span>
            <span class="text-zinc-600">|</span>
            <span class="text-rose-400 font-semibold">${hrvText}</span>
          </div>
        </div>
        <span class="px-2 py-0.5 rounded-full text-[9px] font-black uppercase bg-amber-500/10 text-amber-400 border border-amber-500/30">
          IMPACT
        </span>
      </div>
    `;
  }).join('');
}

export function renderStrainRecoveryBalance(row, customSlice) {
  const dot = document.getElementById("quadrant-user-dot");
  const title = document.getElementById("balance-quadrant-title");
  const badge = document.getElementById("balance-badge");
  const sEl = document.getElementById("balance-7d-strain");
  const rEl = document.getElementById("balance-7d-recovery");

  const slice7d = customSlice || (
    (state.allDailyRecords && state.allDailyRecords.length > 0)
      ? state.allDailyRecords.slice(state.currentDateIndex, state.currentDateIndex + 7)
      : (row ? [row] : [])
  );

  const sVals = slice7d.map(r => Number(r.day_strain)).filter(v => !isNaN(v) && v >= 0);
  const rVals = slice7d.map(r => Number(r.recovery_score || r.recovery)).filter(v => !isNaN(v) && v >= 0);

  const s = sVals.length ? (sVals.reduce((a, b) => a + b, 0) / sVals.length) : (row && row.day_strain != null ? Number(row.day_strain) : null);
  const r = rVals.length ? (rVals.reduce((a, b) => a + b, 0) / rVals.length) : (row && row.recovery_score != null ? Number(row.recovery_score) : null);

  if (sEl) sEl.innerText = s != null ? s.toFixed(1) : "--";
  if (rEl) rEl.innerText = r != null ? Math.round(r) + "%" : "--%";

  if (s == null || r == null) {
    if (title) title.innerText = "Strain vs Recovery Balance";
    if (badge) {
      badge.className = "px-2 py-0.5 rounded-full text-[9px] font-mono font-bold uppercase tracking-wider bg-zinc-800 text-zinc-400 border border-zinc-700";
      badge.innerText = "AWAITING SYNC";
    }
    if (dot) dot.style.display = "none";
    return;
  }

  if (dot) {
    dot.style.display = "flex";
    const xPct = Math.min(90, Math.max(10, (s / 21.0) * 100));
    const yPct = Math.min(90, Math.max(10, 100 - r));
    dot.style.left = xPct + "%";
    dot.style.top = yPct + "%";
  }

  if (title && badge) {
    if (s >= 11.5 && r >= 50) {
      title.innerText = "Optimal Overload (7d)";
      badge.className = "px-2 py-0.5 rounded-full text-[9px] font-mono font-bold uppercase tracking-wider bg-augur-green/10 text-augur-green border border-augur-green/30";
      badge.innerText = "ADAPTING";
    } else if (s >= 11.5 && r < 50) {
      title.innerText = "Overreaching State (7d)";
      badge.className = "px-2 py-0.5 rounded-full text-[9px] font-mono font-bold uppercase tracking-wider bg-rose-500/10 text-rose-400 border border-rose-500/30";
      badge.innerText = "HIGH FATIGUE";
    } else if (s < 11.5 && r >= 50) {
      title.innerText = "Restoring & Primed (7d)";
      badge.className = "px-2 py-0.5 rounded-full text-[9px] font-mono font-bold uppercase tracking-wider bg-cyan-500/10 text-cyan-400 border border-cyan-500/30";
      badge.innerText = "PRIMED";
    } else {
      title.innerText = "Systemic Stress / Detraining";
      badge.className = "px-2 py-0.5 rounded-full text-[9px] font-mono font-bold uppercase tracking-wider bg-amber-500/10 text-amber-400 border border-amber-500/30";
      badge.innerText = "STRESS LOAD";
    }
  }
}

export function renderBiologicalAge(row) {
  const bioEl = document.getElementById("bio-age-val");
  const calEl = document.getElementById("calendar-age-val");
  const deltaEl = document.getElementById("bio-age-delta-badge");
  const vo2El = document.getElementById("bio-vo2-val");
  const rhrEl = document.getElementById("bio-rhr-val");

  if (!row) return;

  const birthYear = (row.user_baselines && row.user_baselines.birth_year) || 2004;
  const calendarAge = new Date().getFullYear() - birthYear;
  const vo2 = (row.user_baselines && row.user_baselines.vo2_max) || 51.5;

  let rhr = row.rhr;
  if (rhr == null && row.vitals_baseline && row.vitals_baseline.rhr) {
    rhr = row.vitals_baseline.rhr.val;
  }
  if (rhr == null) rhr = 45;

  // Jackson et al. / HUNT regression model
  const expectedVo2 = 50.5 - (0.37 * calendarAge);
  const deltaVo2 = (vo2 - expectedVo2) / 0.37;
  const deltaRhr = (50 - rhr) / 5.0;
  const deltaAge = deltaVo2 + deltaRhr;
  const biologicalAge = Math.max(18.0, Math.round((calendarAge - deltaAge) * 10) / 10);
  const diff = Math.round((calendarAge - biologicalAge) * 10) / 10;

  if (bioEl) bioEl.innerText = biologicalAge.toFixed(1);
  if (calEl) calEl.innerText = `${calendarAge} yrs`;
  if (vo2El) vo2El.innerText = `${Number(vo2).toFixed(1)} ml/kg/min`;
  if (rhrEl) rhrEl.innerText = `${Math.round(rhr)} bpm`;

  if (deltaEl) {
    if (diff > 0) {
      deltaEl.className = "px-2 py-0.5 rounded-full text-[9px] font-black uppercase bg-augur-green/10 text-augur-green border border-augur-green/30 inline-block mt-0.5";
      deltaEl.innerText = `-${diff.toFixed(1)} yrs younger`;
    } else if (diff < 0) {
      deltaEl.className = "px-2 py-0.5 rounded-full text-[9px] font-black uppercase bg-amber-500/10 text-amber-400 border border-amber-500/30 inline-block mt-0.5";
      deltaEl.innerText = `+${Math.abs(diff).toFixed(1)} yrs older`;
    } else {
      deltaEl.className = "px-2 py-0.5 rounded-full text-[9px] font-black uppercase bg-zinc-800 text-zinc-400 border border-zinc-700 inline-block mt-0.5";
      deltaEl.innerText = "Baseline match";
    }
  }
}

export function renderTrendsTab(row) {
  if (!row) return;
  const v2 = (row.metrics_v2 && typeof row.metrics_v2 === 'object') ? row.metrics_v2 : {};

  renderAlcoholClearance(v2);
  renderCaffeineClearance(v2, row);
  renderStrainRecoveryBalance(row);
  renderBiologicalAge(row);
  renderHabitCorrelations(row.habit_correlations);
}
