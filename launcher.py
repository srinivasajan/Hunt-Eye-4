from __future__ import annotations

import subprocess
import sys
import os
import threading
from pathlib import Path
from tkinter import (
    BOTH, Button, Frame, Label, StringVar, Tk, Canvas, PhotoImage
)

sys.path.insert(0, os.path.abspath('src'))

if getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS'):
    MEIPASS_ROOT = Path(sys._MEIPASS)
    ROOT = Path(sys.executable).parent
else:
    MEIPASS_ROOT = Path(__file__).resolve().parent
    ROOT = MEIPASS_ROOT

CONFIG_PATH = ROOT / "config.yaml"

_PREVIEW_CANDIDATES = [
    ROOT / "scripts" / "preview.py",
    ROOT / "preview.py",
]

# Colour palette — dark professional theme
_BG         = "#0d1117"   # near-black background
_BG2        = "#161b22"   # card background
_BG3        = "#21262d"   # hover / selected card
_ACCENT     = "#238636"   # green CTA
_ACCENT_HOV = "#2ea043"   # green hover
_BORDER     = "#30363d"   # card border colour
_TEXT       = "#e6edf3"   # primary text
_TEXT_MUT   = "#8b949e"   # muted / secondary text
_WARN       = "#d29922"   # warning amber
_BAD        = "#da3633"   # error red
_GOOD       = "#3fb950"   # status green
_CARD_SEL   = "#1f6feb"   # selected card accent (blue)


def _find_preview() -> Path | None:
    for p in _PREVIEW_CANDIDATES:
        if p.exists():
            return p
    return None


class SourceCard(Frame):
    """A selectable input-source card button."""

    def __init__(self, parent, title: str, subtitle: str,
                 value: str, variable: StringVar, on_select, **kw):
        super().__init__(parent, bg=_BG2, cursor="hand2",
                         highlightthickness=1, highlightbackground=_BORDER,
                         **kw)
        self._value = value
        self._var = variable
        self._on_select = on_select

        self._title_lbl = Label(self, text=title, bg=_BG2,
                                fg=_TEXT, font=("Segoe UI", 11, "bold"))
        self._title_lbl.pack(anchor="w", padx=14, pady=(12, 1))

        self._sub_lbl = Label(self, text=subtitle, bg=_BG2,
                              fg=_TEXT_MUT, font=("Segoe UI", 9),
                              wraplength=170)
        self._sub_lbl.pack(anchor="w", padx=14, pady=(0, 12))

        self._status_lbl = Label(self, text="", bg=_BG2,
                                 fg=_TEXT_MUT, font=("Segoe UI", 8))
        self._status_lbl.pack(anchor="w", padx=14, pady=(0, 8))

        for widget in (self, self._title_lbl, self._sub_lbl, self._status_lbl):
            widget.bind("<Button-1>", self._click)
            widget.bind("<Enter>", self._hover_enter)
            widget.bind("<Leave>", self._hover_leave)

        variable.trace_add("write", lambda *_: self._refresh())
        self._refresh()

    def _click(self, _event=None):
        self._var.set(self._value)
        if self._on_select:
            self._on_select(self._value)

    def _hover_enter(self, _event=None):
        if self._var.get() != self._value:
            self._set_bg(_BG3)

    def _hover_leave(self, _event=None):
        self._refresh()

    def _set_bg(self, colour: str):
        for w in (self, self._title_lbl, self._sub_lbl, self._status_lbl):
            try:
                w.config(bg=colour)
            except Exception:
                pass

    def _refresh(self):
        selected = self._var.get() == self._value
        if selected:
            self.config(highlightbackground=_CARD_SEL, highlightthickness=2)
            self._set_bg(_BG3)
            self._title_lbl.config(fg=_TEXT)
        else:
            self.config(highlightbackground=_BORDER, highlightthickness=1)
            self._set_bg(_BG2)
            self._title_lbl.config(fg=_TEXT_MUT)

    def set_status(self, text: str, colour: str = _TEXT_MUT):
        self._status_lbl.config(text=text, fg=colour)


class HuntEyeApp:
    def __init__(self) -> None:
        self.root = Tk()
        self.root.title("HuntEye")
        self.root.geometry("560x620")
        self.root.resizable(False, False)
        self.root.configure(bg=_BG)

        # Runtime process tracking
        self._runtime_process: subprocess.Popen | None = None
        self._other_processes: list[subprocess.Popen] = []
        self._launched: bool = False

        # Source selection
        self._source = StringVar(value=self._detect_source())

        self._build()

        # Kick off background probe after UI is visible
        self.root.after(300, self._probe_sources)

    def run(self) -> None:
        self.root.protocol("WM_DELETE_WINDOW", self._close)
        self.root.mainloop()

    # ------------------------------------------------------------------
    # UI construction
    # ------------------------------------------------------------------

    def _build(self) -> None:
        # ── Header ────────────────────────────────────────────────────
        header = Frame(self.root, bg=_BG, pady=0)
        header.pack(fill="x", padx=0, pady=0)

        # Top accent bar
        accent_bar = Frame(header, bg=_ACCENT, height=3)
        accent_bar.pack(fill="x")

        title_frame = Frame(header, bg=_BG)
        title_frame.pack(fill="x", padx=28, pady=(20, 4))

        Label(title_frame, text="HUNT", bg=_BG, fg=_TEXT,
              font=("Segoe UI", 28, "bold")).pack(side="left")
        Label(title_frame, text="EYE", bg=_BG, fg=_ACCENT,
              font=("Segoe UI", 28, "bold")).pack(side="left")

        Label(header, text="Autonomous Drone Tracking System",
              bg=_BG, fg=_TEXT_MUT,
              font=("Segoe UI", 10)).pack(anchor="w", padx=28, pady=(0, 16))

        # Divider
        Frame(self.root, bg=_BORDER, height=1).pack(fill="x")

        # ── Source Selection ──────────────────────────────────────────
        Label(self.root, text="SELECT INPUT SOURCE",
              bg=_BG, fg=_TEXT_MUT,
              font=("Segoe UI", 8, "bold")).pack(anchor="w", padx=28, pady=(18, 8))

        cards_frame = Frame(self.root, bg=_BG)
        cards_frame.pack(fill="x", padx=28)

        self._card_sim = SourceCard(
            cards_frame,
            title="Simulator",
            subtitle="Connect to AirSim for simulated flight and tracking.",
            value="SIMULATOR",
            variable=self._source,
            on_select=self._on_source_changed,
            width=155,
        )
        self._card_sim.pack(side="left", padx=(0, 8), fill="y")

        self._card_webcam = SourceCard(
            cards_frame,
            title="Webcam",
            subtitle="Use a connected USB or built-in camera for live tracking.",
            value="WEBCAM",
            variable=self._source,
            on_select=self._on_source_changed,
            width=155,
        )
        self._card_webcam.pack(side="left", padx=(0, 8), fill="y")

        self._card_demo = SourceCard(
            cards_frame,
            title="Demo Mode",
            subtitle="Run without hardware. Synthetic feed with full UI.",
            value="DEMO",
            variable=self._source,
            on_select=self._on_source_changed,
            width=155,
        )
        self._card_demo.pack(side="left", fill="y")

        # ── Status area ────────────────────────────────────────────────
        Frame(self.root, bg=_BORDER, height=1).pack(fill="x", pady=(18, 0))

        self._status_frame = Frame(self.root, bg=_BG2, pady=12)
        self._status_frame.pack(fill="x")

        self._status_icon = Label(self._status_frame, text="○",
                                  bg=_BG2, fg=_TEXT_MUT,
                                  font=("Segoe UI", 14))
        self._status_icon.pack(side="left", padx=(18, 8))

        self._status_lbl = Label(self._status_frame,
                                 text="Checking system...",
                                 bg=_BG2, fg=_TEXT_MUT,
                                 font=("Segoe UI", 10),
                                 wraplength=440, justify="left")
        self._status_lbl.pack(side="left", fill="x", expand=True, padx=(0, 18))

        Frame(self.root, bg=_BORDER, height=1).pack(fill="x")

        # ── Readiness Checklist ────────────────────────────────────────
        Label(self.root, text="SYSTEM CHECK",
              bg=_BG, fg=_TEXT_MUT,
              font=("Segoe UI", 8, "bold")).pack(anchor="w", padx=28, pady=(16, 8))

        check_frame = Frame(self.root, bg=_BG)
        check_frame.pack(fill="x", padx=28)

        self._checks: dict[str, Label] = {}
        checks = [
            ("source",  "Input source"),
            ("config",  "Configuration"),
            ("ai",      "AI detection engine"),
        ]
        for key, label in checks:
            row = Frame(check_frame, bg=_BG)
            row.pack(fill="x", pady=2)
            dot = Label(row, text="○  ", bg=_BG, fg=_TEXT_MUT,
                        font=("Segoe UI Mono", 11))
            dot.pack(side="left")
            Label(row, text=label, bg=_BG, fg=_TEXT_MUT,
                  font=("Segoe UI", 10)).pack(side="left")
            self._checks[key] = dot

        # ── CTA Button ─────────────────────────────────────────────────
        Frame(self.root, bg=_BG, height=12).pack()

        self._btn_launch = Button(
            self.root,
            text="LAUNCH MISSION",
            command=self._launch_mission,
            bg=_ACCENT,
            fg="white",
            activebackground=_ACCENT_HOV,
            activeforeground="white",
            relief="flat",
            pady=16,
            font=("Segoe UI", 13, "bold"),
            cursor="hand2",
        )
        self._btn_launch.pack(fill=BOTH, padx=28, pady=(0, 8))

        # Secondary actions row
        sec_row = Frame(self.root, bg=_BG)
        sec_row.pack(fill="x", padx=28, pady=(0, 4))

        self._btn_preview = self._secondary_btn(sec_row, "Preview Feed", self._start_preview)
        
        # Only show tests in development, not in the frozen packaged build
        if not getattr(sys, 'frozen', False):
            self._btn_preview.pack(side="left", padx=(0, 6), fill="x", expand=True)
            self._btn_check = self._secondary_btn(sec_row, "Run Tests", self._check_system)
            self._btn_check.pack(side="left", fill="x", expand=True)
        else:
            self._btn_preview.pack(fill="x", expand=True)

        # ── Footer ─────────────────────────────────────────────────────
        Frame(self.root, bg=_BORDER, height=1).pack(fill="x", pady=(8, 0))
        self._footer_lbl = Label(
            self.root,
            text="Ready to launch.",
            bg=_BG, fg=_TEXT_MUT,
            font=("Segoe UI", 9),
            wraplength=500, justify="left",
        )
        self._footer_lbl.pack(anchor="w", padx=28, pady=(8, 16))

    def _secondary_btn(self, parent, text: str, command) -> Button:
        return Button(
            parent,
            text=text,
            command=command,
            bg=_BG2,
            fg=_TEXT_MUT,
            activebackground=_BG3,
            activeforeground=_TEXT,
            relief="flat",
            pady=9,
            font=("Segoe UI", 10),
            cursor="hand2",
        )

    # ------------------------------------------------------------------
    # Source detection + probing
    # ------------------------------------------------------------------

    def _detect_source(self) -> str:
        """Infer current mode from config.yaml."""
        if CONFIG_PATH.exists():
            text = CONFIG_PATH.read_text(encoding="utf-8")
            if "backend: real" in text:
                return "WEBCAM"
        return "SIMULATOR"

    def _on_source_changed(self, value: str) -> None:
        self._save_mode(value)
        self._probe_sources()

    def _probe_sources(self) -> None:
        """Run lightweight background checks and update the UI."""
        def _probe():
            results = {}

            # Config check
            results["config"] = CONFIG_PATH.exists()

            # AI models check — check in the bundle directory
            yolo_path = MEIPASS_ROOT / "yolov8n.pt"
            results["ai"] = yolo_path.exists()

            # Source availability
            source = self._source.get()
            if source == "SIMULATOR":
                results["source"] = self._probe_airsim()
            elif source == "WEBCAM":
                results["source"] = self._probe_webcam()
            else:  # DEMO
                results["source"] = True

            # Update UI from main thread
            self.root.after(0, lambda: self._apply_probe_results(results, source))

        threading.Thread(target=_probe, daemon=True).start()
        self._set_status("○", "Checking...", _TEXT_MUT)

    def _probe_airsim(self) -> bool:
        """Quick TCP probe to AirSim port (41451) — no airsim import needed."""
        import socket
        try:
            ip = self._read_airsim_ip()
            with socket.create_connection((ip, 41451), timeout=1.5):
                return True
        except Exception:
            return False

    def _probe_webcam(self) -> bool:
        """Check if any camera index 0 is openable."""
        try:
            import cv2
            cap = cv2.VideoCapture(0)
            ok = cap.isOpened()
            cap.release()
            return ok
        except Exception:
            return False

    def _read_airsim_ip(self) -> str:
        """Extract AirSim IP from config.yaml (default 127.0.0.1)."""
        if not CONFIG_PATH.exists():
            return "127.0.0.1"
        for line in CONFIG_PATH.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line.startswith("ip:"):
                return line.split(":", 1)[1].strip().strip('"').strip("'") or "127.0.0.1"
        return "127.0.0.1"

    def _apply_probe_results(self, results: dict, source: str) -> None:
        # Update check dots
        for key, ok in results.items():
            lbl = self._checks.get(key)
            if lbl:
                lbl.config(text="●  " if ok else "○  ",
                            fg=_GOOD if ok else _TEXT_MUT)

        source_ok = results.get("source", False)
        config_ok = results.get("config", True)
        ai_ok = results.get("ai", False)

        # Update source card statuses
        if source == "SIMULATOR":
            self._card_sim.set_status(
                "● Connected" if source_ok else "○ Not detected",
                _GOOD if source_ok else _TEXT_MUT
            )
        elif source == "WEBCAM":
            self._card_webcam.set_status(
                "● Available" if source_ok else "○ Not detected",
                _GOOD if source_ok else _TEXT_MUT
            )

        # Main status message
        if source == "DEMO":
            self._set_status("●", "Demo Mode — no hardware required.", _GOOD)
            self._check_mark("source", True)
        elif source_ok:
            label = "Simulator connected." if source == "SIMULATOR" else "Camera detected."
            self._set_status("●", label, _GOOD)
        else:
            label = "Simulator not detected." if source == "SIMULATOR" else "No camera detected."
            self._set_status("⚠", f"{label} You can still launch in Demo Mode.", _WARN)

        # AI status card
        self._card_demo.set_status(
            "● Detection ready" if ai_ok else "○ Model not found",
            _GOOD if ai_ok else _TEXT_MUT
        )

    def _check_mark(self, key: str, ok: bool) -> None:
        lbl = self._checks.get(key)
        if lbl:
            lbl.config(text="●  " if ok else "○  ",
                       fg=_GOOD if ok else _TEXT_MUT)

    def _set_status(self, icon: str, text: str, colour: str) -> None:
        self._status_icon.config(text=icon, fg=colour)
        self._status_lbl.config(text=text, fg=colour)

    # ------------------------------------------------------------------
    # Mode persistence
    # ------------------------------------------------------------------

    def _save_mode(self, source: str) -> None:
        if not CONFIG_PATH.exists():
            return
        text = CONFIG_PATH.read_text(encoding="utf-8")
        if source == "WEBCAM":
            text = _replace_yaml_value(text, "system", "mode", "real")
            text = _replace_yaml_value(text, "hal", "backend", "real")
            text = _replace_yaml_value(text, "real", "require_mavlink", "false")
        elif source == "DEMO":
            # Demo mode uses airsim backend config but HAL will fall back to NullBackend
            text = _replace_yaml_value(text, "system", "mode", "demo")
            text = _replace_yaml_value(text, "hal", "backend", "airsim")
        else:
            text = _replace_yaml_value(text, "system", "mode", "sim")
            text = _replace_yaml_value(text, "hal", "backend", "airsim")
        CONFIG_PATH.write_text(text, encoding="utf-8")

    # ------------------------------------------------------------------
    # Actions
    # ------------------------------------------------------------------

    def _launch_mission(self) -> None:
        if self._launched:
            return

        self._launched = True
        self._save_mode(self._source.get())

        # Permanently disable the launch button
        try:
            self._btn_launch.config(
                state="disabled",
                bg="#1a3a22",
                text="LAUNCHING...",
            )
        except Exception:
            pass

        # Set environment variable for runtime
        os.environ["HUNTEYE_SOURCE"] = self._source.get()

        self._set_footer("Mission runtime starting. This window will close.")
        # Give UI time to paint the launching state before blocking the main thread
        self.root.after(1000, self._start_runtime)

    def _start_runtime(self) -> None:
        """Transitions into the tactical runtime within the same process."""
        self._stop_apps()
        self.root.destroy()
        
        # True Single-Exe architecture:
        # Load and run the main entry point cleanly.
        # This resolves PyInstaller's subprocess spawning issues.
        import main
        main.main()

    def _start_preview(self) -> None:
        preview = _find_preview()
        if preview is None:
            self._set_footer("preview.py not found in scripts/ or project root.")
            return
        proc = subprocess.Popen([sys.executable, str(preview)], cwd=ROOT)
        self._other_processes.append(proc)
        self._set_footer("Opening preview window.")

    def _check_system(self) -> None:
        self._set_footer("Running tests — this takes a few seconds...")
        self._btn_check.config(state="disabled")

        def _run():
            result = subprocess.run(
                [sys.executable, "-m", "pytest", "-q"],
                cwd=ROOT,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
            )
            ok = result.returncode == 0
            msg = "All tests passed." if ok else "Some tests failed. Check terminal for details."
            self.root.after(0, lambda: self._finish_check(msg))

        threading.Thread(target=_run, daemon=True).start()

    def _finish_check(self, msg: str) -> None:
        self._set_footer(msg)
        try:
            self._btn_check.config(state="normal")
        except Exception:
            pass

    def _hide_after_launch(self) -> None:
        self.root.withdraw()

    def _stop_apps(self) -> None:
        for process in list(self._other_processes):
            if process.poll() is None:
                process.terminate()
        self._other_processes.clear()

        self._launched = False

    def _set_footer(self, text: str) -> None:
        self._footer_lbl.config(text=text)

    def _close(self) -> None:
        self._stop_apps()
        try:
            self.root.destroy()
        except Exception:
            pass


# ---------------------------------------------------------------------------
# YAML helper (unchanged from original)
# ---------------------------------------------------------------------------

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
