import os
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent

if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

import customtkinter as ctk
import threading
import socket
import cv2

APP_TITLE = "HuntEye"

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("dark-blue")


class SourceCard(ctk.CTkFrame):
    def __init__(self, master, title, desc, source_key, callback):
        super().__init__(
            master,
            corner_radius=0,
            border_width=1,
            border_color="#2a3441",
            fg_color="#111827",
        )

        self.source_key = source_key
        self.callback = callback

        self.grid_columnconfigure(0, weight=1)

        self.title = ctk.CTkLabel(
            self,
            text=title,
            font=("Segoe UI", 18, "bold"),
            text_color="#e5e7eb",
        )
        self.title.grid(row=0, column=0, padx=20, pady=(20, 5), sticky="w")

        self.desc = ctk.CTkLabel(
            self,
            text=desc,
            justify="left",
            wraplength=220,
            font=("Segoe UI", 13),
            text_color="#94a3b8",
        )
        self.desc.grid(row=1, column=0, padx=20, pady=(0, 20), sticky="w")

        self.bind("<Button-1>", self._clicked)
        self.title.bind("<Button-1>", self._clicked)
        self.desc.bind("<Button-1>", self._clicked)

    def _clicked(self, _event):
        self.callback(self.source_key)

    def set_selected(self, selected):
        if selected:
            self.configure(border_color="#2563eb", border_width=2)
        else:
            self.configure(border_color="#2a3441", border_width=1)


class Launcher(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title(APP_TITLE)
        self.geometry("900x620")
        self.resizable(False, False)

        self.selected_source = "SIMULATOR"

        self.grid_columnconfigure(0, weight=1)

        header = ctk.CTkFrame(self, fg_color="#020817", corner_radius=0)
        header.grid(row=0, column=0, sticky="ew")

        title = ctk.CTkLabel(
            header,
            text="HUNT EYE",
            font=("Segoe UI", 42, "bold"),
            text_color="#22c55e",
        )
        title.pack(anchor="w", padx=40, pady=(35, 5))

        subtitle = ctk.CTkLabel(
            header,
            text="Autonomous Drone Tracking System",
            font=("Segoe UI", 16),
            text_color="#94a3b8",
        )
        subtitle.pack(anchor="w", padx=42, pady=(0, 30))

        body = ctk.CTkFrame(self, fg_color="#020817", corner_radius=0)
        body.grid(row=1, column=0, sticky="nsew")

        section = ctk.CTkLabel(
            body,
            text="SELECT INPUT SOURCE",
            font=("Segoe UI", 15, "bold"),
            text_color="#cbd5e1",
        )
        section.pack(anchor="w", padx=40, pady=(20, 10))

        cards = ctk.CTkFrame(body, fg_color="#020817")
        cards.pack(fill="x", padx=40)

        cards.grid_columnconfigure((0, 1, 2), weight=1)

        self.card_sim = SourceCard(
            cards,
            "Simulator",
            "Connect to AirSim for simulated flight and tracking.",
            "SIMULATOR",
            self.select_source,
        )
        self.card_sim.grid(row=0, column=0, padx=8, sticky="nsew")

        self.card_cam = SourceCard(
            cards,
            "Webcam",
            "Use a connected USB or built-in camera for live tracking.",
            "WEBCAM",
            self.select_source,
        )
        self.card_cam.grid(row=0, column=1, padx=8, sticky="nsew")

        self.card_demo = SourceCard(
            cards,
            "Demo Mode",
            "Synthetic tracking feed without hardware.",
            "DEMO",
            self.select_source,
        )
        self.card_demo.grid(row=0, column=2, padx=8, sticky="nsew")

        self.select_source("SIMULATOR")

        self.status = ctk.CTkLabel(
            body,
            text="Simulator not detected. You can still launch in Demo Mode.",
            text_color="#f59e0b",
            font=("Segoe UI", 14),
        )
        self.status.pack(anchor="w", padx=42, pady=25)

        self.launch_btn = ctk.CTkButton(
            body,
            text="LAUNCH MISSION",
            height=60,
            corner_radius=0,
            fg_color="#16a34a",
            hover_color="#15803d",
            font=("Segoe UI", 22, "bold"),
            command=self.launch,
        )
        self.launch_btn.pack(fill="x", padx=40, pady=(10, 30))

    def select_source(self, source):
        self.selected_source = source

        self.card_sim.set_selected(source == "SIMULATOR")
        self.card_cam.set_selected(source == "WEBCAM")
        self.card_demo.set_selected(source == "DEMO")

    def launch(self):
        import traceback
        os.environ["HUNTEYE_SOURCE"] = self.selected_source

        self.destroy()

        try:
            import main
            main.main()
        except Exception as e:
            tb = traceback.format_exc()
            # Write crash log next to the EXE / script so it's always findable
            log_path = os.path.join(os.path.dirname(os.path.abspath(sys.argv[0])), "crash_log.txt")
            try:
                with open(log_path, "w") as f:
                    f.write(f"=== HuntEye Runtime Crash ===\n{tb}\n")
            except Exception:
                pass
            print(f"\n[FATAL] HuntEye crashed: {e}\nTraceback written to crash_log.txt")
            print(tb)


if __name__ == "__main__":
    app = Launcher()
    app.mainloop()