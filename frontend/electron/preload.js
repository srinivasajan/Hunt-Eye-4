const { contextBridge, ipcRenderer } = require("electron");

contextBridge.exposeInMainWorld("huntEye", {
  startRuntime: (mode) => ipcRenderer.invoke("runtime:start", mode),
  stopRuntime: () => ipcRenderer.invoke("runtime:stop"),
  checkSystem: () => ipcRenderer.invoke("system:check"),
  onRuntimeStatus: (callback) => {
    ipcRenderer.on("runtime-status", (_event, payload) => callback(payload));
  },
  onRuntimeLog: (callback) => {
    ipcRenderer.on("runtime-log", (_event, payload) => callback(payload));
  },
});
