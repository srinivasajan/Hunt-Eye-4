from __future__ import annotations

import subprocess
import sys
import os
from pathlib import Path
from tkinter import BOTH, Button, Frame, Label, StringVar, Tk

# Add src to the Python path to allow imports from the src directory
sys.path.insert(0, os.path.abspath('src'))

ROOT = Path(__file__).resolve().parent
CONFIG_PATH = ROOT / "config.yaml"


class HuntEyeApp:
    def __init__(self) -> None:
        self.root = Tk()
        self.root.title("HuntEye")
        self.root.geometry("520x390")
        self.root.resizable(False, False)
        self.root.configure(bg="#111827")

        self.mode = StringVar(value=self._detect_mode())
        self.processes: list[subprocess.Popen] = []

        self._build()

    def run(self) -> None:
        self.root.protocol("WM_DELETE_WINDOW", self._close)
        self.root.mainloop()

    def _build(self) -> None:
        Label(
            self.root,
            text="HuntEye",
            bg="#111827",
            fg="white",
            font=("Segoe UI", 30, "bold"),
        ).pack(pady=(28, 4))

        Label(
            self.root,
            text="Simple launcher",
            bg="#111827",
            fg="#9ca3af",
            font=("Segoe UI", 12),
        ).pack(pady=(0, 24))

        mode_box = Frame(self.root, bg="#111827")
        mode_box.pack(pady=(0, 18))

        self._small_button(mode_box, "Use Simulator", lambda: self._set_mode("airsim")).pack(
            side="left", padx=6
        )
        self._small_button(mode_box, "Use Webcam", lambda: self._set_mode("webcam")).pack(
            side="left", padx=6
        )

        self.mode_label = Label(
            self.root,
            text="",
            bg="#111827",
            fg="#d1d5db",
            font=("Segoe UI", 11),
        )
        self.mode_label.pack(pady=(0, 16))
        self._refresh_mode_label()

        self._main_button("START HUNTEYE", self._start_hunteye).pack(fill=BOTH, padx=60, pady=6)
        self._main_button("PREVIEW SCREEN", self._start_preview).pack(fill=BOTH, padx=60, pady=6)
        self._main_button("CHECK IF OK", self._check_system).pack(fill=BOTH, padx=60, pady=6)

        self.status = Label(
            self.root,
            text="Ready.",
            bg="#111827",
            fg="#93c5fd",
            font=("Segoe UI", 10),
            wraplength=430,
        )
        self.status.pack(pady=(18, 8))

        Button(
            self.root,
            text="Stop opened apps",
            command=self._stop_apps,
            bg="#374151",
            fg="white",
            activebackground="#4b5563",
            activeforeground="white",
            relief="flat",
            padx=14,
            pady=7,
            font=("Segoe UI", 9),
        ).pack()

    def _main_button(self, text: str, command) -> Button:
        return Button(
            self.root,
            text=text,
            command=command,
            bg="#2563eb",
            fg="white",
            activebackground="#1d4ed8",
            activeforeground="white",
            relief="flat",
            pady=13,
            font=("Segoe UI", 12, "bold"),
        )

    def _small_button(self, parent, text: str, command) -> Button:
        return Button(
            parent,
            text=text,
            command=command,
            bg="#1f2937",
            fg="white",
            activebackground="#374151",
            activeforeground="white",
            relief="flat",
            padx=16,
            pady=8,
            font=("Segoe UI", 10),
        )

    def _detect_mode(self) -> str:
        text = CONFIG_PATH.read_text(encoding="utf-8") if CONFIG_PATH.exists() else ""
        return "webcam" if "backend: real" in text else "airsim"

    def _set_mode(self, mode: str) -> None:
        self.mode.set(mode)
        self._save_mode()
        self._refresh_mode_label()

    def _refresh_mode_label(self) -> None:
        if self.mode.get() == "airsim":
            self.mode_label.config(text="Current mode: Simulator")
        else:
            self.mode_label.config(text="Current mode: Webcam")

    def _save_mode(self) -> None:
        text = CONFIG_PATH.read_text(encoding="utf-8")
        if self.mode.get() == "airsim":
            text = _replace_yaml_value(text, "system", "mode", "sim")
            text = _replace_yaml_value(text, "hal", "backend", "airsim")
        else:
            text = _replace_yaml_value(text, "system", "mode", "real")
            text = _replace_yaml_value(text, "hal", "backend", "real")
            text = _replace_yaml_value(text, "real", "require_mavlink", "false")
        CONFIG_PATH.write_text(text, encoding="utf-8")

    def _start_hunteye(self) -> None:
        self._save_mode()
        self._start([sys.executable, "main.py"])
        self._say("Starting HuntEye. A camera window should open.")

    def _start_preview(self) -> None:
        self._start([sys.executable, "preview.py"])
        self._say("Opening one simple preview window.")

    def _check_system(self) -> None:
        self._say("Checking. Give it a few seconds...")
        result = subprocess.run(
            [sys.executable, "-m", "pytest", "-q"],
            cwd=ROOT,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
        )
        if result.returncode == 0:
            self._say("Looks OK.")
        else:
            self._say("Something failed. Send me a screenshot of this app.")

    def _start(self, command: list[str]) -> None:
        process = subprocess.Popen(command, cwd=ROOT)
        self.processes.append(process)

    def _stop_apps(self) -> None:
        for process in list(self.processes):
            if process.poll() is None:
                process.terminate()
        self.processes.clear()
        self._say("Stopped apps opened from this launcher.")

    def _say(self, text: str) -> None:
        self.status.config(text=text)

    def _close(self) -> None:
        self._stop_apps()
        self.root.destroy()


def _replace_yaml_value(text: str, section: str, key: str, value: str) -> str:
    lines = text.splitlines()
    in_section = False

    for index, line in enumerate(lines):
        if line.startswith(f"{section}:"):
            in_section = True
            continue
        if in_section and line and not line.startswith(" "):
            in_section = False
        if in_section and line.strip().startswith(f"{key}:"):
            indent = line[: len(line) - len(line.lstrip(" "))]
            lines[index] = f"{indent}{key}: {value}"
            return "\n".join(lines) + "\n"

    return text


if __name__ == "__main__":
    HuntEyeApp().run()
