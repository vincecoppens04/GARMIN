/**
 * AUGUR Sports Science & Recovery Intelligence
 * Main Application Orchestrator (ES Module)
 */

import { state, loadSettings } from './state.js';
import { supabaseClient, getSupabaseClient, fetchTelemetryFromCloud, triggerCloudSync } from './api.js';
import { renderTodayTab } from './tabs/todayTab.js';
import { renderSleepTab, updateSleepSimulator, renderCircadianWindows } from './tabs/sleepTab.js';
import { renderStrainTab, renderStrainCurve } from './tabs/strainTab.js';
import {
  renderTrendsTab,
  renderAlcoholClearance,
  renderCaffeineClearance,
  updateCaffeineSimulator,
  adjustCaffeineCups,
  onCaffeineHourChanged,
  renderStrainRecoveryBalance,
  renderBiologicalAge,
  renderHabitCorrelations
} from './tabs/trendsTab.js';
import {
  renderAnalyticsTab,
  renderAcwrGauge,
  renderTrainingMonotony,
  renderCardiovascularPolarization,
  renderDaytimeStressBalance,
  renderAnalyticsGraphs,
  setGlobalTimeRange,
  getHistoryForRange
} from './tabs/analyticsTab.js';
import {
  openSettingsModal,
  closeSettingsModal,
  saveSettings,
  applySettings,
  triggerTestNotification,
  subscribeOneSignal,
  handleSignOut,
  updatePushStatusUI
} from './modals/settingsModal.js';
import {
  openHabitModal,
  closeHabitModal,
  saveHabitLog,
  checkHabitBannerStatus
} from './modals/habitModal.js';
import {
  openVitalsModal,
  closeVitalsModal,
  renderVitalsTable
} from './components/vitalsCards.js';
import {
  showExplanation,
  closeExplanation
} from './components/explanations.js';

console.log(
  "%c[AUGUR ARCHITECTURE]%c Clean Modular ES Architecture v2.0 Active\n" +
  "  ├── Engine: engine/models/day_record.py + engine/calculators/*\n" +
  "  ├── Tabs: todayTab.js, sleepTab.js, strainTab.js, trendsTab.js, analyticsTab.js\n" +
  "  └── Style: css/style.css\n" +
  "Branch: code_restructuring",
  "color: #00E599; font-weight: bold; font-size: 12px;",
  "color: #00F0FF; font-size: 11px;"
);
window.__AUGUR_MODULAR__ = true;

// =================================================================
// OVERLAY & AUTH HELPERS
// =================================================================
export function showLoadingOverlay(msg) {
  const loading = document.getElementById("app-loading-overlay");
  const statusText = document.getElementById("loading-status-text");
  if (statusText && msg) statusText.innerText = msg;
  if (loading) {
    loading.classList.remove("hidden");
    loading.style.opacity = "1";
    loading.style.pointerEvents = "auto";
  }
}

export function hideLoadingOverlay() {
  const loading = document.getElementById("app-loading-overlay");
  if (loading && !loading.classList.contains("hidden")) {
    loading.style.opacity = "0";
    loading.style.pointerEvents = "none";
    setTimeout(() => {
      loading.classList.add("hidden");
    }, 500);
  }
}

export function onAuthenticated(user) {
  state.user = user;
  const overlay = document.getElementById("auth-overlay");
  const app = document.getElementById("app");
  if (overlay) overlay.classList.add("hidden");
  if (app) app.classList.remove("hidden");

  showLoadingOverlay("Synchronizing physiological telemetry...");

  const emailEl = document.getElementById("settings-account-email");
  if (emailEl && user && user.email) {
    emailEl.innerText = user.email;
  }

  loadTelemetry();
}

export function showLoginOverlay() {
  state.user = null;
  hideLoadingOverlay();
  const overlay = document.getElementById("auth-overlay");
  const app = document.getElementById("app");
  if (overlay) overlay.classList.remove("hidden");
  if (app) app.classList.add("hidden");
}

export async function handleLogin(e) {
  if (e) e.preventDefault();
  const email = document.getElementById("login-email")?.value.trim();
  const password = document.getElementById("login-password")?.value;
  const errEl = document.getElementById("login-error");
  const btn = document.getElementById("btn-login");

  if (errEl) errEl.classList.add("hidden");
  if (btn) {
    btn.disabled = true;
    btn.innerText = "Authenticating...";
  }

  try {
    if (!supabaseClient) throw new Error("Supabase auth engine not initialized");
    const { data, error } = await supabaseClient.auth.signInWithPassword({ email, password });
    if (error) throw error;
    if (data && data.user) {
      onAuthenticated(data.user);
    }
  } catch (err) {
    if (errEl) {
      errEl.innerText = err.message || "Invalid authentication credentials";
      errEl.classList.remove("hidden");
    }
  } finally {
    if (btn) {
      btn.disabled = false;
      btn.innerText = "Sign In";
    }
  }
}

export async function initAuth() {
  loadSettings();

  const isLocal = (
    typeof window !== "undefined" &&
    (window.location.hostname === "localhost" ||
     window.location.hostname === "127.0.0.1" ||
     window.location.protocol === "file:")
  );

  const client = getSupabaseClient ? getSupabaseClient() : null;
  if (!client) {
    console.warn("Supabase client not loaded, opening app directly");
    onAuthenticated({ email: "vincecoppens04" });
    return;
  }

  try {
    const { data: { session }, error } = await client.auth.getSession();
    if (session && session.user) {
      onAuthenticated(session.user);
    } else if (isLocal) {
      console.info("Local environment detected: auto-authenticating developer session");
      onAuthenticated({ email: "vincecoppens04" });
    } else {
      showLoginOverlay();
    }
  } catch (err) {
    console.warn("Session retrieval exception:", err);
    if (isLocal) {
      onAuthenticated({ email: "vincecoppens04" });
    } else {
      showLoginOverlay();
    }
  }

  try {
    client.auth.onAuthStateChange((event, session) => {
      if (event === "SIGNED_OUT") {
        showLoginOverlay();
      } else if (event === "SIGNED_IN" && session && session.user) {
        onAuthenticated(session.user);
      }
    });
  } catch (e) {
    console.warn("Auth state change listener warning:", e);
  }
}

// =================================================================
// DATE NAVIGATION & TELEMETRY INGESTION
// =================================================================
export function updateDateSwitcherUI() {
  const prevBtn = document.getElementById("btn-date-prev");
  const nextBtn = document.getElementById("btn-date-next");
  const dateLabel = document.getElementById("date-label");

  if (!state.allDailyRecords || state.allDailyRecords.length <= 1) {
    if (prevBtn) {
      prevBtn.disabled = true;
      prevBtn.classList.add("opacity-30", "cursor-not-allowed", "text-zinc-600");
      prevBtn.classList.remove("hover:bg-zinc-800", "text-zinc-400", "hover:text-white");
    }
    if (nextBtn) {
      nextBtn.disabled = true;
      nextBtn.classList.add("opacity-30", "cursor-not-allowed", "text-zinc-600");
      nextBtn.classList.remove("hover:bg-zinc-800", "text-zinc-400", "hover:text-white");
    }
  } else {
    if (nextBtn) {
      const isAtLatest = (state.currentDateIndex <= 0);
      nextBtn.disabled = isAtLatest;
      if (isAtLatest) {
        nextBtn.classList.add("opacity-30", "cursor-not-allowed", "text-zinc-600");
        nextBtn.classList.remove("hover:bg-zinc-800", "text-zinc-400", "hover:text-white");
      } else {
        nextBtn.classList.remove("opacity-30", "cursor-not-allowed", "text-zinc-600");
        nextBtn.classList.add("hover:bg-zinc-800", "text-zinc-400", "hover:text-white");
      }
    }

    if (prevBtn) {
      const isAtOldest = (state.currentDateIndex >= state.allDailyRecords.length - 1);
      prevBtn.disabled = isAtOldest;
      if (isAtOldest) {
        prevBtn.classList.add("opacity-30", "cursor-not-allowed", "text-zinc-600");
        prevBtn.classList.remove("hover:bg-zinc-800", "text-zinc-400", "hover:text-white");
      } else {
        prevBtn.classList.remove("opacity-30", "cursor-not-allowed", "text-zinc-600");
        prevBtn.classList.add("hover:bg-zinc-800", "text-zinc-400", "hover:text-white");
      }
    }
  }

  if (dateLabel) {
    if (state.currentDateIndex === 0) {
      dateLabel.innerText = "TODAY";
    } else if (state.currentDateIndex === 1) {
      dateLabel.innerText = "YESTERDAY";
    } else {
      const rec = state.allDailyRecords[state.currentDateIndex];
      if (rec && rec.date) {
        const parts = rec.date.split("-");
        if (parts.length >= 3) {
          const d = new Date(Number(parts[0]), Number(parts[1]) - 1, Number(parts[2]));
          dateLabel.innerText = d.toLocaleDateString('en-US', { month: 'short', day: 'numeric' }).toUpperCase();
        } else {
          dateLabel.innerText = rec.date;
        }
      } else {
        dateLabel.innerText = `DAY -${state.currentDateIndex}`;
      }
    }
  }
}

export function navigateDay(delta) {
  if (!state.allDailyRecords || state.allDailyRecords.length === 0) return;
  const newOffset = state.currentDateIndex + delta;
  if (newOffset < 0 || newOffset >= state.allDailyRecords.length) return;
  state.currentDateIndex = newOffset;

  const rec = state.allDailyRecords[state.currentDateIndex];
  const fullRec = {
    ...rec,
    history_records: state.allDailyRecords,
    user_baselines: state.allDailyRecords[0]?.user_baselines,
    habit_correlations: state.allDailyRecords[0]?.habit_correlations,
  };
  populateUI(fullRec);
}

export function populateUI(row) {
  if (!row) return;
  state.cachedTelemetry = row;

  updateDateSwitcherUI();

  // Tab 1: Today
  renderTodayTab(row);

  // Tab 2: Sleep & Health
  renderSleepTab(row);

  // Tab 3: Activities & Strain
  renderStrainTab(row);

  // Tab 4: Trends & Insights
  renderTrendsTab(row);

  // Tab 5: Analytics
  renderAnalyticsTab(row);

  // System Diagnostics Readout in settings modal
  const hrv = row.hrv_rmssd != null ? Math.round(row.hrv_rmssd) : 94;
  const rhr = row.rhr != null ? Math.round(row.rhr) : 45;
  const diagHrv = document.getElementById("diag-hrv-base");
  const diagRhr = document.getElementById("diag-rhr-base");
  const diagVo2 = document.getElementById("diag-vo2-base");
  if (diagHrv) diagHrv.innerText = `${hrv} ms (±13.2)`;
  if (diagRhr) diagRhr.innerText = `${rhr} bpm (±2.0)`;
  if (diagVo2) diagVo2.innerText = (row.user_baselines && row.user_baselines.vo2_max) ? `${row.user_baselines.vo2_max} ml/kg/min` : "51.5 ml/kg/min";

  const settingsHrv = document.getElementById("settings-hrv-base");
  const settingsRhr = document.getElementById("settings-rhr-base");
  const settingsVo2 = document.getElementById("settings-vo2-base");
  if (settingsHrv) settingsHrv.innerText = `${hrv} ms (±11)`;
  if (settingsRhr) settingsRhr.innerText = `${rhr} bpm (±3)`;
  if (settingsVo2) settingsVo2.innerText = (row.user_baselines && row.user_baselines.vo2_max) ? `${row.user_baselines.vo2_max} ml/kg/min` : "51.5 ml/kg/min";

  checkHabitBannerStatus(row.date);
  applySettings();

  const syncEl = document.getElementById("last-sync-time");
  if (syncEl) syncEl.innerText = "SYNCED";
}

export async function loadTelemetry() {
  try {
    const row = await fetchTelemetryFromCloud();
    if (row && (row.recovery_score != null || row.recovery != null)) {
      if (row.history_records && Array.isArray(row.history_records) && row.history_records.length > 0) {
        state.allDailyRecords = row.history_records;
        state.allDailyRecords[0] = { ...row, ...state.allDailyRecords[0] };
      } else {
        state.allDailyRecords = [row];
      }
      state.currentDateIndex = 0;
      populateUI(state.allDailyRecords[0]);
      hideLoadingOverlay();
      return;
    }
  } catch (err) {
    console.warn("Modal read error, checking Supabase:", err);
  }

  const statusText = document.getElementById("loading-status-text");
  if (statusText) statusText.innerText = "Querying encrypted database...";

  if (supabaseClient) {
    try {
      const { data } = await supabaseClient
        .from("daily_summaries")
        .select("*")
        .order("date", { ascending: false })
        .limit(90);

      if (data && data.length > 0) {
        state.allDailyRecords = data;
        state.currentDateIndex = 0;
        const fullRec = { ...data[0], history_records: data };
        populateUI(fullRec);
      }
    } catch (err) {
      console.error("Supabase load error:", err);
    }
  }
  hideLoadingOverlay();
}

export async function triggerModalSync() {
  const btn = document.getElementById("btn-sync-telemetry");
  const btnText = document.getElementById("sync-button-text");
  const spinner = document.getElementById("sync-spinner");
  const pulse = document.getElementById("sync-pulse");

  try {
    if (btn) btn.disabled = true;
    if (spinner) spinner.classList.add("animate-spin");
    if (pulse) pulse.className = "w-1.5 h-1.5 rounded-full bg-augur-cyan animate-ping";
    if (btnText) btnText.innerText = "Syncing with Garmin Cloud...";

    const result = await triggerCloudSync();

    if (result && result.history_records && Array.isArray(result.history_records) && result.history_records.length > 0) {
      state.allDailyRecords = result.history_records;
      state.allDailyRecords[0] = { ...result, ...state.allDailyRecords[0] };
    } else if (result) {
      state.allDailyRecords = [result];
    }
    state.currentDateIndex = 0;
    populateUI(state.allDailyRecords[0]);
    applySettings();

    if (btnText) btnText.innerText = "✓ Telemetry Updated";
    if (pulse) pulse.className = "w-1.5 h-1.5 rounded-full bg-augur-green";
    setTimeout(() => {
      if (btnText) btnText.innerText = "Sync Telemetry";
      if (spinner) spinner.classList.remove("animate-spin");
      if (btn) btn.disabled = false;
    }, 2500);
  } catch (e) {
    console.error("Sync error:", e);
    if (btnText) btnText.innerText = "Sync Error (Retry)";
    if (spinner) spinner.classList.remove("animate-spin");
    if (btn) btn.disabled = false;
    setTimeout(() => {
      if (btnText) btnText.innerText = "Sync Telemetry";
    }, 3000);
  }
}

// =================================================================
// 5-TAB NAVIGATION SYSTEM
// =================================================================
export function switchTab(tabName) {
  const tabs = ['today', 'sleep', 'strain', 'trends', 'analytics'];
  state.currentTab = tabName;
  tabs.forEach(t => {
    const section = document.getElementById(`tab-${t}`);
    const btn = document.getElementById(`nav-${t}`);
    const isCurrent = t === tabName;
    if (section) section.classList.toggle("hidden", !isCurrent);
    if (btn) {
      btn.classList.toggle("text-augur-green", isCurrent);
      btn.classList.toggle("text-zinc-500", !isCurrent);
      const dot = btn.querySelector("span:last-child");
      if (dot) {
        dot.classList.toggle("bg-augur-green", isCurrent);
        dot.classList.toggle("bg-transparent", !isCurrent);
      }
    }
  });
  if (tabName === 'trends' || tabName === 'analytics') {
    setGlobalTimeRange(state.currentRangeDays || 30);
  }
}

// =================================================================
// GLOBAL BINDINGS (Exposed to window for HTML inline handlers)
// =================================================================
window.switchTab = switchTab;
window.navigateDay = navigateDay;
window.triggerModalSync = triggerModalSync;
window.openSettingsModal = openSettingsModal;
window.closeSettingsModal = closeSettingsModal;
window.saveSettings = saveSettings;
window.triggerTestNotification = triggerTestNotification;
window.subscribeOneSignal = subscribeOneSignal;
window.handleSignOut = handleSignOut;
window.openHabitModal = openHabitModal;
window.closeHabitModal = closeHabitModal;
window.saveHabitLog = saveHabitLog;
window.openVitalsModal = openVitalsModal;
window.closeVitalsModal = closeVitalsModal;
window.showExplanation = showExplanation;
window.closeExplanation = closeExplanation;
window.closeExplanationModal = closeExplanation;
window.setGlobalTimeRange = setGlobalTimeRange;
window.adjustCaffeineCups = adjustCaffeineCups;
window.onCaffeineHourChanged = onCaffeineHourChanged;
window.updateSleepSimulator = updateSleepSimulator;
window.handleLogin = handleLogin;
window.bypassLoginForDev = () => onAuthenticated({ email: "vincecoppens04" });
window.updatePushStatusUI = updatePushStatusUI;

// Initialize on DOM ready or immediately if DOM is already parsed
if (typeof document !== "undefined") {
  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", initAuth);
  } else {
    initAuth();
  }
}
