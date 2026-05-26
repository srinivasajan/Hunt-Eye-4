const { app, BrowserWindow, ipcMain } = require("electron");
const path = require("path");
const fs = require("fs");
const { spawn } = require("child_process");

// rootDir will point to the main project folder (e.g., the folder containing main.py and config.yaml)
const rootDir = path.resolve(__dirname, "..", "..");
const configPath = path.join(rootDir, "config.yaml");

let mainWindow = null;
let activeProcess = null;

function createWindow() {
  mainWindow = new BrowserWindow({
    width: 1180,
    height: 760,
    minWidth: 980,
    minHeight: 640,
    title: "HuntEye",
    backgroundColor: "#0f172a",
    webPreferences: {
      preload: path.join(__dirname, "preload.js"),
      contextIsolation: true,
      nodeIntegration: false,
    },
  });

  mainWindow.loadFile(path.join(__dirname, "renderer", "index.html"));
}

function send(channel, payload) {
  if (mainWindow && !mainWindow.isDestroyed()) {
    mainWindow.webContents.send(channel, payload);
  }
}

function pythonCommand() {
  return process.env.HUNTEYE_PYTHON || "python";
}

function setMode(mode) {
  let text = fs.readFileSync(configPath, "utf8");
  if (mode === "airsim") {
    text = replaceYamlValue(text, "system", "mode", "sim");
    text = replaceYamlValue(text, "hal", "backend", "airsim");
  } else if (mode === "webcam") {
    text = replaceYamlValue(text, "system", "mode", "real");
    text = replaceYamlValue(text, "hal", "backend", "real");
    text = replaceYamlValue(text, "real", "require_mavlink", "false");
  }
  fs.writeFileSync(configPath, text, "utf8");
}

function replaceYamlValue(text, section, key, value) {
  const lines = text.split(/\r?\n/);
  let inSection = false;

  for (let index = 0; index < lines.length; index += 1) {
    const line = lines[index];
    if (line.startsWith(`${section}:`)) {
      inSection = true;
      continue;
    }
    if (inSection && line && !line.startsWith(" ")) {
      inSection = false;
    }
    if (inSection && line.trim().startsWith(`${key}:`)) {
      const indent = line.slice(0, line.length - line.trimStart().length);
      lines[index] = `${indent}${key}: ${value}`;
      return `${lines.join("\n")}\n`;
    }
  }

  return text;
}

function friendlyLine(line) {
  if (!line) return null;
  if (line.includes("WSAECONNREFUSED") || line.includes("Retry connection")) {
    return "AirSim is not open or not reachable. Open AirSim first, or switch to Practice mode.";
  }
  if (line.includes("CameraWorker") && line.includes("stale")) {
    return "Waiting for camera frames...";
  }
  if (line.includes("No module named")) {
    return "A required component is missing. Run System Check, then send the result.";
  }
  if (line.includes("HuntEye runtime starting")) {
    return "HuntEye is starting.";
  }
  if (line.includes("Worker crashed")) {
    return "One background part stopped. Check the selected mode and connections.";
  }
  return null;
}

function startRuntime(mode) {
  stopRuntime();
  setMode(mode);

  activeProcess = spawn(pythonCommand(), ["main.py"], {
    cwd: rootDir,
    windowsHide: true,
    stdio: ["ignore", "pipe", "pipe"],
  });

  send("runtime-status", {
    state: "starting",
    message: mode === "airsim" ? "Starting with AirSim..." : "Starting with webcam...",
  });

  const handleLine = (chunk) => {
    const lines = chunk.toString().split(/\r?\n/);
    for (const line of lines) {
      const friendly = friendlyLine(line);
      if (friendly) {
        send("runtime-log", { message: friendly });
      }
    }
  };

  activeProcess.stdout.on("data", handleLine);
  activeProcess.stderr.on("data", handleLine);

  activeProcess.on("exit", (code) => {
    activeProcess = null;
    send("runtime-status", {
      state: "stopped",
      message: code === 0 ? "HuntEye stopped." : "HuntEye stopped. Check the selected mode.",
    });
  });
}

function stopRuntime() {
  if (activeProcess && !activeProcess.killed) {
    activeProcess.kill();
  }
  activeProcess = null;
}

function runSystemCheck() {
  return new Promise((resolve) => {
    const check = spawn(pythonCommand(), ["-m", "pytest", "-q"], {
      cwd: rootDir,
      windowsHide: true,
      stdio: ["ignore", "pipe", "pipe"],
    });

    let output = "";
    check.stdout.on("data", (chunk) => {
      output += chunk.toString();
    });
    check.stderr.on("data", (chunk) => {
      output += chunk.toString();
    });
    check.on("exit", (code) => {
      resolve({
        ok: code === 0,
        summary: code === 0 ? "Everything looks ready." : "Something needs attention.",
        details: output.trim(),
      });
    });
  });
}

ipcMain.handle("runtime:start", (_event, mode) => {
  startRuntime(mode);
  return { ok: true };
});

ipcMain.handle("runtime:stop", () => {
  stopRuntime();
  return { ok: true };
});

ipcMain.handle("system:check", async () => runSystemCheck());

app.whenReady().then(createWindow);

app.on("window-all-closed", () => {
  stopRuntime();
  if (process.platform !== "darwin") app.quit();
});

app.on("activate", () => {
  if (BrowserWindow.getAllWindows().length === 0) createWindow();
});
