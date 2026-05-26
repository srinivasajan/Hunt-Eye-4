const pages = document.querySelectorAll(".page");
const navItems = document.querySelectorAll(".nav-item");
const modeCards = document.querySelectorAll(".mode-card:not(.locked)");
const selectedModeLabel = document.getElementById("selectedMode");
const startButton = document.getElementById("startButton");
const stopButton = document.getElementById("stopButton");
const emergencyButton = document.getElementById("emergencyButton");
const plainLog = document.getElementById("plainLog");
const runtimeStatus = document.getElementById("runtimeStatus");
const checkButton = document.getElementById("checkButton");
const checkResult = document.getElementById("checkResult");
const canvas = document.getElementById("practiceCanvas");
const emptyScreen = document.getElementById("emptyScreen");
const ctx = canvas.getContext("2d");

let selectedMode = "practice";
let practiceRunning = false;
let animationId = null;
let startedAt = performance.now();

const modeNames = {
  practice: "Practice Mode",
  webcam: "Webcam Mode",
  airsim: "AirSim Mode",
};

navItems.forEach((item) => {
  item.addEventListener("click", () => {
    navItems.forEach((nav) => nav.classList.remove("active"));
    item.classList.add("active");
    pages.forEach((page) => page.classList.remove("active"));
    document.getElementById(item.dataset.page).classList.add("active");
  });
});

modeCards.forEach((card) => {
  card.addEventListener("click", () => {
    selectedMode = card.dataset.mode;
    modeCards.forEach((item) => item.classList.remove("selected"));
    card.classList.add("selected");
    selectedModeLabel.textContent = modeNames[selectedMode];
    log(`Selected ${modeNames[selectedMode]}.`);
  });
});

document.querySelector('[data-mode="practice"]').classList.add("selected");

startButton.addEventListener("click", async () => {
  if (selectedMode === "practice") {
    startPractice();
    return;
  }

  stopPractice();
  setStatus("Starting");
  log(
    selectedMode === "airsim"
      ? "Starting AirSim mode. If AirSim is closed, this will not connect."
      : "Starting webcam mode. Allow camera access if Windows asks."
  );
  await window.huntEye.startRuntime(selectedMode);
});

stopButton.addEventListener("click", async () => {
  stopPractice();
  await window.huntEye.stopRuntime();
  setStatus("Stopped");
  log("Stopped.");
});

emergencyButton.addEventListener("click", async () => {
  stopPractice();
  await window.huntEye.stopRuntime();
  setStatus("Emergency Stop");
  log("Emergency stop pressed. Background control has been stopped.");
});

checkButton.addEventListener("click", async () => {
  checkResult.textContent = "Checking...";
  const result = await window.huntEye.checkSystem();
  checkResult.textContent = result.ok
    ? `${result.summary}\n\n${result.details}`
    : `${result.summary}\n\n${result.details}`;
});

window.huntEye.onRuntimeStatus((payload) => {
  setStatus(payload.message || payload.state);
  log(payload.message || payload.state);
});

window.huntEye.onRuntimeLog((payload) => {
  log(payload.message);
});

function startPractice() {
  practiceRunning = true;
  startedAt = performance.now();
  emptyScreen.style.display = "none";
  setStatus("Practice Running");
  log("Practice mode is running. This is safe and does not use a real drone.");
  drawPractice();
}

function stopPractice() {
  practiceRunning = false;
  if (animationId) cancelAnimationFrame(animationId);
  animationId = null;
}

function drawPractice() {
  if (!practiceRunning) return;
  const t = (performance.now() - startedAt) / 1000;
  const w = canvas.width;
  const h = canvas.height;

  const sky = ctx.createLinearGradient(0, 0, 0, h);
  sky.addColorStop(0, "#182238");
  sky.addColorStop(0.52, "#101827");
  sky.addColorStop(0.53, "#16331f");
  sky.addColorStop(1, "#0d1d13");
  ctx.fillStyle = sky;
  ctx.fillRect(0, 0, w, h);

  ctx.strokeStyle = "rgba(148, 163, 184, 0.18)";
  ctx.lineWidth = 1;
  for (let x = 0; x < w; x += 80) {
    ctx.beginPath();
    ctx.moveTo(x, 0);
    ctx.lineTo(x, h);
    ctx.stroke();
  }
  for (let y = 0; y < h; y += 80) {
    ctx.beginPath();
    ctx.moveTo(0, y);
    ctx.lineTo(w, y);
    ctx.stroke();
  }

  const targetX = w / 2 + Math.sin(t * 0.75) * 220;
  const targetY = h / 2 + Math.cos(t * 0.55) * 95;

  ctx.fillStyle = "#35c46b";
  ctx.fillRect(targetX - 24, targetY - 36, 48, 72);

  ctx.strokeStyle = "#33d17a";
  ctx.lineWidth = 4;
  ctx.strokeRect(targetX - 62, targetY - 82, 124, 164);

  ctx.fillStyle = "rgba(51, 209, 122, 0.14)";
  ctx.fillRect(targetX - 62, targetY - 82, 124, 164);

  ctx.fillStyle = "#33d17a";
  ctx.font = "700 24px Segoe UI";
  ctx.fillText("TARGET LOCK", 28, 42);

  ctx.fillStyle = "#cbd5e1";
  ctx.font = "18px Segoe UI";
  ctx.fillText("Mode: Practice", 28, 74);
  ctx.fillText("Safety: Active", 28, 102);
  ctx.fillText(`FPS: ${Math.round(58 + Math.sin(t) * 3)}`, 28, 130);

  ctx.strokeStyle = "rgba(255, 255, 255, 0.55)";
  ctx.lineWidth = 2;
  ctx.beginPath();
  ctx.moveTo(w / 2 - 18, h / 2);
  ctx.lineTo(w / 2 + 18, h / 2);
  ctx.moveTo(w / 2, h / 2 - 18);
  ctx.lineTo(w / 2, h / 2 + 18);
  ctx.stroke();

  animationId = requestAnimationFrame(drawPractice);
}

function setStatus(text) {
  runtimeStatus.textContent = text;
}

function log(message) {
  plainLog.textContent = message;
}
