/**
 * Workout Feed Card Component
 * Renders activity cards with optical HR recovery (HRR 60s/120s), glycogen refuel, and strain metrics.
 */

export function renderWorkoutFeed(activities) {
  const container = document.getElementById("workout-feed-list");
  const countEl = document.getElementById("tab3-feed-count");
  if (!container) return;

  const acts = (activities && activities.length > 0) ? activities.slice(0, 5) : [];
  if (countEl) countEl.innerText = `${acts.length} Recent Sessions`;

  if (acts.length === 0) {
    container.innerHTML = `
      <div class="p-4 rounded-2xl bg-augur-cardInner border border-augur-border text-center text-xs text-zinc-500 font-mono">
        No structured workouts logged for this period
      </div>`;
    return;
  }

  container.innerHTML = acts.map(act => {
    const type = (act.activity_type || "workout").toLowerCase();
    const name = act.name || "Workout";
    const strain = act.workout_strain != null ? Number(act.workout_strain).toFixed(1) : "0.0";
    const durM = Math.floor((act.duration_sec || 0) / 60);
    const durS = (act.duration_sec || 0) % 60;
    const durStr = durM >= 60 ? `${Math.floor(durM / 60)}h ${durM % 60}m` : `${durM}:${durS.toString().padStart(2, '0')}`;
    const distKm = act.distance_m ? (act.distance_m / 1000.0).toFixed(2) + " km" : null;
    const avgHr = act.avg_hr ? `${act.avg_hr} bpm` : "--";
    const load = act.garmin_load != null ? `Load: ${act.garmin_load}` : null;
    const te = act.aerobic_te != null ? `Aerobic TE: ${act.aerobic_te}` : null;

    // V2 features for workout:
    const v2Act = act.metrics_v2 || {};
    const hrr60 = act.hrr_60s != null ? act.hrr_60s : v2Act.hrr_60s;
    const hrr120 = act.hrr_120s != null ? act.hrr_120s : v2Act.hrr_120s;
    const hrrBench = act.hrr_benchmark || v2Act.hrr_benchmark;
    const glyKcal = act.glycogen_depleted_kcal != null ? act.glycogen_depleted_kcal : v2Act.glycogen_depleted_kcal;
    const carbRefuel = act.carb_refuel_target_g != null ? act.carb_refuel_target_g : v2Act.carb_refuel_target_g;
    const sriMin = act.stress_recovery_min != null ? act.stress_recovery_min : v2Act.stress_recovery_min;

    const hrrVal = hrr60 != null ? `-${hrr60} bpm` : (hrr120 != null ? `-${hrr120} bpm` : '-- bpm');
    const hrrSub = hrr60 != null ? `/ 60s ${hrr120 != null ? `(-${hrr120} 2m)` : ''}` : (hrr120 != null ? '/ 120s' : '/ 60s');
    const hasHrr = hrr60 != null || hrr120 != null;

    let iconSvg = '';
    if (type.includes("run")) {
      iconSvg = '<svg class="w-4 h-4 text-emerald-400" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 10V3L4 14h7v7l9-11h-7z" /></svg>';
    } else if (type.includes("cycl") || type.includes("bike")) {
      iconSvg = '<svg class="w-4 h-4 text-cyan-400" fill="none" viewBox="0 0 24 24" stroke="currentColor"><circle cx="5.5" cy="17.5" r="3.5" stroke-width="2"/><circle cx="18.5" cy="17.5" r="3.5" stroke-width="2"/><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 6h-3l-3 6.5h6.5l2-4.5M9 12.5L12 17.5" /></svg>';
    } else if (type.includes("swim")) {
      iconSvg = '<svg class="w-4 h-4 text-blue-400" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M3 15a4 4 0 004 4h10a4 4 0 004-4M3 9a4 4 0 014-4h10a4 4 0 014 4" /></svg>';
    } else if (type.includes("walk")) {
      iconSvg = '<svg class="w-4 h-4 text-amber-400" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M16 11V7a4 4 0 00-8 0v4M5 9h14l1 12H4L5 9z" /></svg>';
    } else {
      iconSvg = '<svg class="w-4 h-4 text-purple-400" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 6h16M4 12h16m-7 6h7" /></svg>';
    }

    return `
      <div class="glass-card border border-augur-border rounded-2xl p-4 shadow-lg space-y-2.5">
        <div class="flex items-center justify-between">
          <div class="flex items-center space-x-2.5">
            <div class="w-8 h-8 rounded-xl bg-augur-cardInner border border-augur-border flex items-center justify-center shrink-0">
              ${iconSvg}
            </div>
            <div>
              <span class="text-xs font-bold text-white block leading-tight">${name}</span>
              <span class="text-[9px] font-mono text-zinc-500 uppercase">${act.date || 'Recent'}</span>
            </div>
          </div>
          <div class="text-right">
            <span class="text-[9px] font-mono text-zinc-500 uppercase block">Activity Strain</span>
            <span class="px-2 py-0.5 rounded-full text-xs font-black font-mono bg-augur-cyan/10 text-augur-cyan border border-augur-cyan/30 inline-block mt-0.5">
              ${strain}
            </span>
          </div>
        </div>

        <div class="grid grid-cols-3 gap-2 text-center font-mono text-[10px] py-1 border-y border-augur-border/40">
          <div class="p-1 rounded-lg bg-augur-cardInner/60">
            <span class="text-zinc-500 block text-[8px] uppercase">Duration</span>
            <span class="text-zinc-200 font-bold">${durStr}</span>
          </div>
          <div class="p-1 rounded-lg bg-augur-cardInner/60">
            <span class="text-zinc-500 block text-[8px] uppercase">${distKm ? 'Distance' : 'Calories'}</span>
            <span class="text-zinc-200 font-bold">${distKm || (act.calories ? act.calories + ' kcal' : '--')}</span>
          </div>
          <div class="p-1 rounded-lg bg-augur-cardInner/60">
            <span class="text-zinc-500 block text-[8px] uppercase">Avg HR</span>
            <span class="text-zinc-200 font-bold">${avgHr}</span>
          </div>
        </div>

        <!-- V2 Metabolic & Autonomic Recovery Badges -->
        <div class="grid grid-cols-2 gap-2 font-mono text-[9px] pt-1">
          <div class="p-2 rounded-xl bg-augur-cardInner/80 border border-augur-border/60">
            <div class="flex items-center justify-between"><span class="text-zinc-500 block text-[8px] uppercase">HR Recovery (HRR)</span><button onclick="showExplanation('hrr')" class="w-3.5 h-3.5 rounded-full bg-zinc-800 hover:bg-zinc-700 text-zinc-400 hover:text-white inline-flex items-center justify-center text-[8px] font-bold focus:outline-none" title="Explanation">?</button></div>
            <div class="flex items-baseline space-x-1.5 mt-0.5">
              <span class="${hasHrr ? 'text-xs font-black text-augur-green' : 'text-xs font-black text-zinc-500'}">${hrrVal}</span>
              <span class="text-[8px] text-zinc-400">${hrrSub}</span>
            </div>
            <span class="text-[8px] ${hrrBench ? 'text-augur-green' : 'text-zinc-500'} block truncate mt-0.5">${hrrBench || 'Awaiting HR Recovery'}</span>
          </div>
          <div class="p-2 rounded-xl bg-augur-cardInner/80 border border-augur-border/60">
            <div class="flex items-center justify-between"><span class="text-zinc-500 block text-[8px] uppercase">Glycogen & Refuel</span><button onclick="showExplanation('glycogen_refuel')" class="w-3.5 h-3.5 rounded-full bg-zinc-800 hover:bg-zinc-700 text-zinc-400 hover:text-white inline-flex items-center justify-center text-[8px] font-bold focus:outline-none" title="Explanation">?</button></div>
            <div class="flex items-baseline space-x-1.5 mt-0.5">
              <span class="${glyKcal != null ? 'text-xs font-black text-amber-400' : 'text-xs font-black text-zinc-500'}">${glyKcal != null ? `${glyKcal} kcal` : '-- kcal'}</span>
              <span class="text-[8px] text-zinc-400">depleted</span>
            </div>
            <span class="text-[8px] ${carbRefuel != null ? 'text-amber-400 font-bold' : 'text-zinc-500'} block mt-0.5">Target: ${carbRefuel != null ? `+${carbRefuel}g Carbs` : '--'}</span>
          </div>
        </div>

        <div class="flex items-center justify-between text-[10px] font-mono text-zinc-400 pt-0.5 border-t border-augur-border/30">
          <span class="text-[9px] text-zinc-500 flex items-center gap-1"><span>Post-workout Calm (SRI): <strong class="${sriMin != null ? 'text-augur-cyan font-bold' : 'text-zinc-500'}">${sriMin != null ? `${sriMin}m` : '--'}</strong> ${sriMin != null ? 'to stress <25' : ''}</span><button onclick="showExplanation('stress_recovery_index')" class="w-3.5 h-3.5 rounded-full bg-zinc-800 hover:bg-zinc-700 text-zinc-400 hover:text-white inline-flex items-center justify-center text-[8px] font-bold focus:outline-none" title="Explanation">?</button></span>
          ${(load || te) ? `<span class="text-augur-green font-bold">${te || load}</span>` : ''}
        </div>
      </div>
    `;
  }).join('');
}
