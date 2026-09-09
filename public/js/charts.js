/**
 * AUGUR SVG Charting Engine & Touch/Pointer Scrubbers
 */

import { state } from "./state.js";

export function drawSvgLine(pathId, values, minVal, maxVal, width = 320, height = 80, padY = 10) {
  const path = document.getElementById(pathId);
  if (!path) return;
  if (!values || !values.length) {
    path.setAttribute("d", "");
    return;
  }
  const validVals = values.map(v => Number(v)).filter(v => !isNaN(v));
  if (!validVals.length) {
    path.setAttribute("d", "");
    return;
  }
  const n = validVals.length;
  const actualMin = Math.min(...validVals);
  const actualMax = Math.max(...validVals);
  const effMin = Math.min(minVal, actualMin);
  const effMax = Math.max(maxVal, actualMax);
  const range = (effMax - effMin) || 1;
  const usableH = height - (padY * 2);

  if (n === 1) {
    const clamped = Math.min(effMax, Math.max(effMin, validVals[0]));
    const y = (height - padY) - ((clamped - effMin) / range) * usableH;
    path.setAttribute("d", `M 0,${y.toFixed(1)} L ${width},${y.toFixed(1)}`);
    return;
  }

  const pts = validVals.map((val, i) => {
    const x = (i / Math.max(1, n - 1)) * width;
    const clamped = Math.min(effMax, Math.max(effMin, val));
    const y = (height - padY) - ((clamped - effMin) / range) * usableH;
    return `${i === 0 ? 'M' : 'L'} ${x.toFixed(1)},${y.toFixed(1)}`;
  }).join(' ');
  path.setAttribute("d", pts);
}

export function drawSvgBars(groupId, values, maxVal, colorFn, width = 320, height = 80) {
  const group = document.getElementById(groupId);
  if (!group) return;
  while (group.firstChild) {
    group.removeChild(group.firstChild);
  }
  if (!values || !values.length) return;

  const n = values.length;
  const barWidth = Math.max(2, Math.min(28, (width / n) - 2));
  const usableH = height - 10;
  const svgNS = "http://www.w3.org/2000/svg";

  values.forEach((rawVal, i) => {
    const val = Number(rawVal) || 0;
    const x = (i / n) * width + 2;
    const h = Math.min(usableH, Math.max(3, (val / maxVal) * usableH));
    const y = (height - 5) - h;
    const color = typeof colorFn === 'function' ? colorFn(val, i) : colorFn;

    const rect = document.createElementNS(svgNS, "rect");
    rect.setAttribute("x", x.toFixed(1));
    rect.setAttribute("y", y.toFixed(1));
    rect.setAttribute("width", barWidth.toFixed(1));
    rect.setAttribute("height", h.toFixed(1));
    rect.setAttribute("rx", "2");
    rect.setAttribute("fill", color);
    group.appendChild(rect);
  });
}

export function formatDateShort(dateStr) {
  if (!dateStr) return "";
  const parts = dateStr.split("-");
  if (parts.length < 3) return dateStr;
  const d = new Date(Number(parts[0]), Number(parts[1]) - 1, Number(parts[2]));
  const month = d.toLocaleDateString([], { month: "short" });
  const day = d.getDate();
  return `${month} ${day}`;
}

export const activeScrubberData = {
  hrv: [],
  rhr: [],
  sleep: [],
  strain: [],
  resp: [],
  spo2: []
};
let scrubbersAttached = false;

export function attachScrubber(containerId, lineId, tipId, readoutId, formatFn, resetFn) {
  const container = document.getElementById(containerId);
  const line = document.getElementById(lineId);
  const tip = document.getElementById(tipId);
  const readout = document.getElementById(readoutId);
  if (!container || !line || !tip) return;

  const handleMove = (e) => {
    const rect = container.getBoundingClientRect();
    const clientX = e.clientX || (e.touches && e.touches[0] ? e.touches[0].clientX : 0);
    if (clientX === undefined) return;
    const x = Math.max(0, Math.min(rect.width, clientX - rect.left));
    const pct = rect.width > 0 ? (x / rect.width) : 0;

    const totalPoints = activeScrubberData.hrv.length || 7;
    const idx = Math.min(totalPoints - 1, Math.max(0, Math.round(pct * (totalPoints - 1))));

    const info = formatFn(idx);
    if (!info) return;

    line.style.left = `${x}px`;
    line.classList.remove("hidden");

    tip.innerText = info.tip;
    tip.style.left = `${Math.min(rect.width - 50, Math.max(50, x))}px`;
    tip.classList.remove("hidden");

    if (readout && info.readout) {
      readout.innerText = info.readout;
    }
  };

  const handleEnd = () => {
    line.classList.add("hidden");
    tip.classList.add("hidden");
    if (readout && resetFn) {
      readout.innerText = resetFn();
    }
  };

  container.addEventListener("pointerdown", (e) => {
    container.setPointerCapture(e.pointerId);
    handleMove(e);
  });
  container.addEventListener("pointermove", handleMove);
  container.addEventListener("pointerup", handleEnd);
  container.addEventListener("pointercancel", handleEnd);
  container.addEventListener("pointerleave", handleEnd);
}

export function setupChartScrubbers() {
  if (scrubbersAttached) return;
  scrubbersAttached = true;

  attachScrubber("container-hrv-chart", "scrubber-line-hrv", "scrubber-tip-hrv", "analytics-hrv-readout", (idx) => {
    const item = activeScrubberData.hrv[idx];
    if (!item) return null;
    return {
      tip: `${item.date} • ${item.val} ms`,
      readout: `${item.date} • HRV: ${item.val} ms (Selected)`
    };
  }, () => {
    const dCount = state.currentRangeDays || 7;
    const vals = activeScrubberData.hrv.map(d => d.val);
    if (!vals.length) return `Latest: -- ms | ${dCount}d Mean: -- ms`;
    const avg = Math.round(vals.reduce((a, b) => a + b, 0) / vals.length);
    const latest = vals[vals.length - 1];
    return `Latest: ${latest} ms | ${dCount}d Mean: ${avg} ms`;
  });

  attachScrubber("container-rhr-chart", "scrubber-line-rhr", "scrubber-tip-rhr", "analytics-rhr-readout", (idx) => {
    const item = activeScrubberData.rhr[idx];
    if (!item) return null;
    return {
      tip: `${item.date} • ${item.val} bpm`,
      readout: `${item.date} • RHR: ${item.val} bpm (Selected)`
    };
  }, () => {
    const dCount = state.currentRangeDays || 7;
    const vals = activeScrubberData.rhr.map(d => d.val);
    if (!vals.length) return `Latest: -- bpm | ${dCount}d Mean: -- bpm | Floor: -- bpm`;
    const avg = Math.round(vals.reduce((a, b) => a + b, 0) / vals.length);
    const floor = Math.min(...vals);
    const latest = vals[vals.length - 1];
    return `Latest: ${latest} bpm | ${dCount}d Mean: ${avg} bpm | Floor: ${floor} bpm`;
  });

  attachScrubber("container-sleep-chart", "scrubber-line-sleep", "scrubber-tip-sleep", "analytics-sleep-readout", (idx) => {
    const item = activeScrubberData.sleep[idx];
    if (!item) return null;
    const sH = Math.floor(item.val);
    const sM = Math.round((item.val - sH) * 60);
    return {
      tip: `${item.date} • ${sH}h ${sM}m`,
      readout: `${item.date} • Slept: ${sH}h ${sM}m`
    };
  }, () => {
    const baseNeedMin = state.settings.sleep_need_min || 435;
    const baseNeedStr = `${Math.floor(baseNeedMin / 60)}h ${baseNeedMin % 60}m`;
    const vals = activeScrubberData.sleep.map(d => d.val);
    if (!vals.length) return `Avg: --h --m / Need: ${baseNeedStr}`;
    const avg = vals.reduce((a, b) => a + b, 0) / vals.length;
    const sH = Math.floor(avg);
    const sM = Math.round((avg - sH) * 60);
    return `Avg: ${sH}h ${sM}m / Need: ${baseNeedStr}`;
  });

  attachScrubber("container-strain-chart", "scrubber-line-strain", "scrubber-tip-strain", "analytics-strain-readout", (idx) => {
    const item = activeScrubberData.strain[idx];
    if (!item) return null;
    return {
      tip: `${item.date} • ${item.val.toFixed(1)} Strain`,
      readout: `${item.date} • Day Strain: ${item.val.toFixed(1)} / 21.0`
    };
  }, () => {
    const dCount = state.currentRangeDays || 7;
    const vals = activeScrubberData.strain.map(d => d.val);
    if (!vals.length) return `${dCount}d Avg Strain: -- / 21.0`;
    const avg = (vals.reduce((a, b) => a + b, 0) / vals.length).toFixed(1);
    return `${dCount}d Avg Strain: ${avg} / 21.0`;
  });

  attachScrubber("container-vitals-chart", "scrubber-line-vitals", "scrubber-tip-vitals", "analytics-vitals-readout", (idx) => {
    const rItem = activeScrubberData.resp[idx];
    const sItem = activeScrubberData.spo2[idx];
    if (!rItem || !sItem) return null;
    return {
      tip: `${rItem.date} • ${rItem.val.toFixed(1)} RPM | ${Math.round(sItem.val)}% SpO2`,
      readout: `${rItem.date} • Resp: ${rItem.val.toFixed(1)} br/min | SpO2: ${Math.round(sItem.val)}%`
    };
  }, () => {
    const rVals = activeScrubberData.resp.map(d => d.val);
    const sVals = activeScrubberData.spo2.map(d => d.val);
    if (!rVals.length && !sVals.length) return `RPM: -- br/min | SpO2: --%`;
    const rLatest = rVals.length ? rVals[rVals.length - 1] : null;
    const sLatest = sVals.length ? sVals[sVals.length - 1] : null;
    const rStr = rLatest != null ? `${rLatest.toFixed(1)} br/min` : "-- br/min";
    const sStr = sLatest != null ? `${Math.round(sLatest)}%` : "--%";
    return `Latest: ${rStr} | ${sStr}`;
  });
}
