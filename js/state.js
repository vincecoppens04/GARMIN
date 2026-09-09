/**
 * AUGUR Sports Science & Recovery Intelligence - Central Reactive State Store
 */

export const DEFAULT_SETTINGS = {
  max_hr: 202,
  sleep_need_min: 435,
  target_wake_time: "07:00",
  debt_payback_pct: 0.33,
  notifications: { morning: true, habit: true, anomaly: true, bedtime: true }
};

export const state = {
  settings: { ...DEFAULT_SETTINGS },
  cachedTelemetry: null,
  allDailyRecords: [],
  currentDateIndex: 0,
  currentTab: "today",
  currentRangeDays: 30,
  selectedCaffeineCups: 2,
  selectedCaffeineHour: 11,
  user: null,
};

export function loadSettings() {
  try {
    const saved = localStorage.getItem("augur_settings");
    if (saved) {
      const parsed = JSON.parse(saved);
      state.settings = { ...DEFAULT_SETTINGS, ...parsed };
      if (parsed.notifications) {
        state.settings.notifications = { ...DEFAULT_SETTINGS.notifications, ...parsed.notifications };
      }
    }
  } catch (e) {
    console.warn("Failed to load settings:", e);
  }
  return state.settings;
}

export function saveSettings(newSettings) {
  try {
    state.settings = { ...state.settings, ...newSettings };
    localStorage.setItem("augur_settings", JSON.stringify(state.settings));
  } catch (e) {
    console.warn("Failed to persist settings:", e);
  }
}

export function getCurrentRecord() {
  if (!state.allDailyRecords || state.allDailyRecords.length === 0) {
    return state.cachedTelemetry ? state.cachedTelemetry.summary : null;
  }
  return state.allDailyRecords[state.currentDateIndex] || null;
}
