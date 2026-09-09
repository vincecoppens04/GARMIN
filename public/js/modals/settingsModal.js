/**
 * Settings & Diagnostics Modal Controller
 * Handles user physiological baseline overrides (Max HR, baseline sleep need,
 * wake time, sleep debt payback rate), push notification authorization,
 * cloud sync, and instant metric recalculation across the UI.
 */

import { state, saveSettings as persistSettings } from '../state.js';
import { saveSettingsToCloud, sendTestPush, signOutUser } from '../api.js';
import { setGlobalTimeRange } from '../tabs/analyticsTab.js';
import { updateSleepSimulator, renderCircadianWindows } from '../tabs/sleepTab.js';
import { renderCaffeineClearance } from '../tabs/trendsTab.js';

export function applySettings() {
  const row = (state.allDailyRecords && state.allDailyRecords.length > 0 && state.currentDateIndex >= 0 && state.currentDateIndex < state.allDailyRecords.length)
    ? state.allDailyRecords[state.currentDateIndex]
    : state.cachedTelemetry;
  if (!row) return;

  const baseMin = state.settings.sleep_need_min || 435;
  const baseH = Math.floor(baseMin / 60);
  const baseM = baseMin % 60;

  const strain = row.day_strain != null ? Number(row.day_strain) : 0;
  const debtMin = row.sleep_debt_min != null ? row.sleep_debt_min : 0;
  const actualSec = row.sleep_actual_sec || 24300;
  const actH = Math.floor(actualSec / 3600);
  const actM = Math.floor((actualSec % 3600) / 60);

  // Recalculate Tonight's Sleep Need Equation (harmonized with engine/calculators/sleep.py)
  const strainDemand = Math.max(0, Math.floor(Math.max(0, (strain - 10.0) * 4.8)));
  const debtRate = state.settings.debt_payback_pct != null ? state.settings.debt_payback_pct : 0.33;
  const debtPayback = Math.min(45, Math.max(0, Math.round(debtMin * debtRate)));
  const totalNeedMin = baseMin + strainDemand + debtPayback;
  const needH = Math.floor(totalNeedMin / 60);
  const needM = totalNeedMin % 60;

  // Update Tab 2
  const tab2Target = document.getElementById("tab2-sleep-target");
  if (tab2Target) tab2Target.innerText = `${needH}h ${needM.toString().padStart(2, '0')}m`;

  const eqBase = document.getElementById("tab2-eq-base");
  if (eqBase) eqBase.innerText = `${baseH}h ${baseM.toString().padStart(2, '0')}m (Base)`;

  const eqStrain = document.getElementById("tab2-eq-strain");
  if (eqStrain) eqStrain.innerText = `${strainDemand}m (Strain)`;

  const eqDebt = document.getElementById("tab2-eq-debt");
  if (eqDebt) eqDebt.innerText = `${debtPayback}m (Debt)`;

  const tab2BedtimeClock = document.getElementById("tab2-bedtime-clock");
  if (tab2BedtimeClock) {
    const wakeTime = state.settings.target_wake_time || "07:00";
    const [wakeH, wakeM] = wakeTime.split(":").map(Number);
    const wakeMinuteOfDay = (wakeH * 60) + wakeM;
    const totalBedtimeMin = totalNeedMin + 15;
    let bedtimeMinuteOfDay = wakeMinuteOfDay - totalBedtimeMin;
    while (bedtimeMinuteOfDay < 0) bedtimeMinuteOfDay += 1440;
    bedtimeMinuteOfDay = bedtimeMinuteOfDay % 1440;
    const bH = Math.floor(bedtimeMinuteOfDay / 60);
    const bM = bedtimeMinuteOfDay % 60;
    tab2BedtimeClock.innerText = `${bH.toString().padStart(2, '0')}:${bM.toString().padStart(2, '0')}`;
  }

  // Update Tab 1
  const sleepActualVal = document.getElementById("sleep-actual-val");
  const sleepNeedVal = document.getElementById("sleep-need-val");
  if (sleepActualVal) sleepActualVal.innerText = `${actH}h ${actM.toString().padStart(2, '0')}m`;
  if (sleepNeedVal) sleepNeedVal.innerText = `${needH}h ${needM.toString().padStart(2, '0')}m`;

  // Update Tab 5 Graphs & Readouts with active settings
  setGlobalTimeRange(state.currentRangeDays || 30);

  // Update Sleep Simulator with active settings
  const simSlider = document.getElementById("v2-sim-slider");
  if (simSlider) updateSleepSimulator(simSlider.value);

  // Re-anchor Circadian Windows and Caffeine Clearance to active wake & bedtime targets
  renderCircadianWindows(row.metrics_v2);
  renderCaffeineClearance(row.metrics_v2, row);
}

export function populateSettingsUI() {
  const setVal = (id, val) => { const el = document.getElementById(id); if (el) el.value = val; };

  setVal("setting-max-hr", state.settings.max_hr);
  setVal("setting-sleep-need", state.settings.sleep_need_min);
  setVal("setting-wake-time", state.settings.target_wake_time || "07:00");
  setVal("setting-debt-rate", state.settings.debt_payback_pct);
}

export function openSettingsModal() {
  populateSettingsUI();
  updatePushStatusUI();
  const modal = document.getElementById("settings-modal");
  if (modal) modal.classList.remove("hidden");
}

export function closeSettingsModal() {
  const modal = document.getElementById("settings-modal");
  if (modal) modal.classList.add("hidden");
}

export async function saveSettings() {
  const getVal = (id, def) => { const el = document.getElementById(id); return el ? el.value : def; };

  const updated = {
    max_hr: Number(getVal("setting-max-hr", 202)),
    sleep_need_min: Number(getVal("setting-sleep-need", 435)),
    target_wake_time: getVal("setting-wake-time", "07:00"),
    debt_payback_pct: Number(getVal("setting-debt-rate", 0.33))
  };

  persistSettings(updated);
  closeSettingsModal();
  applySettings();

  try {
    await saveSettingsToCloud({
      max_hr: updated.max_hr,
      sleep_need_min: updated.sleep_need_min,
      target_wake_time: updated.target_wake_time,
      debt_payback_rate: updated.debt_payback_pct,
    });
  } catch (err) {
    console.warn("Backend settings sync warning:", err);
  }
}

export async function triggerTestNotification() {
  const btn = document.getElementById("btn-test-notif");
  const feedback = document.getElementById("test-notif-feedback");
  const originalText = btn ? btn.innerText : "Send Test Push";

  if (btn) {
    btn.disabled = true;
    btn.innerText = "Dispatching via Modal...";
  }
  if (feedback) {
    feedback.classList.remove("hidden");
    feedback.innerText = "Connecting to Modal cloud & OneSignal...";
    feedback.className = "px-3 py-2 rounded-xl bg-augur-cardInner border border-augur-border text-[11px] font-mono leading-relaxed text-zinc-400";
  }

  try {
    const data = await sendTestPush();
    const recCount = data.recipients != null ? data.recipients : (data.delivered ? 1 : 0);
    if (btn) {
      btn.innerText = `✓ Dispatched (${recCount} dev)`;
      btn.className = "px-2.5 py-1 rounded-lg bg-augur-green text-black font-bold font-mono text-xs transition-all shadow-sm";
    }
    if (feedback) {
      if (data.delivered || recCount > 0) {
        feedback.innerHTML = `
          <div class="text-augur-green font-bold mb-0.5">✓ Dispatched via Modal Cloud & OneSignal:</div>
          <div class="text-white text-xs font-sans font-medium mb-1">${data.title || 'AUGUR Live Telemetry'}</div>
          <div class="text-zinc-300 text-[11px]">${data.message || 'Telemetry dispatched to lock screen'}</div>
        `;
      } else {
        feedback.innerHTML = `
          <div class="text-amber-400 font-bold mb-0.5">⚠ Dispatched to OneSignal (0 devices subscribed):</div>
          <div class="text-zinc-300 text-[11px]">Please tap <strong class="text-white">Enable Push</strong> above to register this iPhone as a subscriber.</div>
        `;
      }
    }
    setTimeout(() => {
      if (btn) {
        btn.disabled = false;
        btn.innerText = originalText;
        btn.className = "px-2.5 py-1 rounded-lg bg-augur-card border border-augur-borderLight text-xs font-bold font-mono text-augur-green hover:bg-augur-green hover:text-black transition-all";
      }
    }, 6000);
  } catch (err) {
    console.error("Cloud push dispatch error:", err);
    if (btn) {
      btn.innerText = "✗ Failed";
      btn.className = "px-2.5 py-1 rounded-lg bg-red-500/20 text-red-400 font-bold font-mono text-xs border border-red-500/40";
    }
    if (feedback) {
      feedback.innerHTML = `<span class="text-red-400 font-bold">Cloud Error:</span> ${err.message || 'Check network connection'}`;
    }
    setTimeout(() => {
      if (btn) {
        btn.disabled = false;
        btn.innerText = originalText;
        btn.className = "px-2.5 py-1 rounded-lg bg-augur-card border border-augur-borderLight text-xs font-bold font-mono text-augur-green hover:bg-augur-green hover:text-black transition-all";
      }
    }, 4000);
  }
}

export async function updatePushStatusUI() {
  const statusEl = document.getElementById("onesignal-sub-status");
  const btn = document.getElementById("btn-onesignal-subscribe");
  if (!statusEl || !btn) return;

  if (window.OneSignal && window.OneSignal.User && window.OneSignal.User.PushSubscription) {
    const isOptedIn = window.OneSignal.User.PushSubscription.optedIn;
    const subId = window.OneSignal.User.PushSubscription.id;
    if (isOptedIn && subId) {
      statusEl.innerText = "✓ Active & Subscribed";
      statusEl.className = "text-[11px] font-mono text-augur-green";
      btn.innerText = "Subscribed";
      btn.disabled = true;
      btn.className = "px-3 py-1.5 rounded-xl bg-augur-card border border-augur-green/40 text-augur-green font-bold font-mono text-xs opacity-80 cursor-default";
      return;
    }
  }

  if ("Notification" in window && Notification.permission === "granted") {
    statusEl.innerText = "Authorized (linking...)";
    statusEl.className = "text-[11px] font-mono text-zinc-300";
  } else if ("Notification" in window && Notification.permission === "denied") {
    statusEl.innerText = "Blocked in iOS Settings";
    statusEl.className = "text-[11px] font-mono text-red-400";
    btn.innerText = "Blocked";
    btn.disabled = true;
    btn.className = "px-3 py-1.5 rounded-xl bg-zinc-800 text-zinc-500 font-bold font-mono text-xs cursor-not-allowed";
  } else {
    statusEl.innerText = "Tap to authorize alerts";
    statusEl.className = "text-[11px] font-mono text-zinc-400";
    btn.innerText = "Enable Push";
    btn.disabled = false;
    btn.className = "px-3 py-1.5 rounded-xl bg-augur-green text-black font-bold font-mono text-xs hover:opacity-90 active:scale-95 transition-all";
  }
}

export async function subscribeOneSignal() {
  const statusEl = document.getElementById("onesignal-sub-status");
  const btn = document.getElementById("btn-onesignal-subscribe");
  if (btn) {
    btn.innerText = "Authorizing...";
    btn.disabled = true;
  }

  try {
    if (window.OneSignalDeferred) {
      window.OneSignalDeferred.push(async function (OneSignal) {
        try {
          if (OneSignal.Notifications && OneSignal.Notifications.requestPermission) {
            await OneSignal.Notifications.requestPermission();
          }
          if (OneSignal.User && OneSignal.User.PushSubscription && OneSignal.User.PushSubscription.optIn) {
            await OneSignal.User.PushSubscription.optIn();
          }
          setTimeout(updatePushStatusUI, 1000);
        } catch (err) {
          console.warn("OneSignal optIn error:", err);
          if (statusEl) statusEl.innerText = "Failed: " + (err.message || err);
        }
      });
    } else if ("Notification" in window) {
      await Notification.requestPermission();
      updatePushStatusUI();
    }
  } catch (e) {
    console.error("Subscription error:", e);
  } finally {
    setTimeout(updatePushStatusUI, 1500);
  }
}

export async function handleSignOut() {
  await signOutUser();
  const authModal = document.getElementById("auth-modal");
  if (authModal) authModal.classList.remove("hidden");
  closeSettingsModal();
}
