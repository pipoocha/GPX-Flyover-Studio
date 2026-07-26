from __future__ import annotations

import subprocess
import sys
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

import yaml


DEFAULT_PROJECT = Path("projects/kagbeni_sangda_v14.yaml")


class FlyoverStudioGUI(tk.Tk):
    def __init__(self):
        super().__init__()

        self.title("GPX Flyover Studio — Réglages")
        self.geometry("820x720")

        self.project_file = tk.StringVar(value=str(DEFAULT_PROJECT))
        self.gpx_file = tk.StringVar()
        self.project_title = tk.StringVar(value="GPX Flyover Studio")

        self.video_duration = tk.IntVar(value=30)
        self.video_fps = tk.IntVar(value=20)
        self.video_size = tk.StringVar(value="1280x720")
        self.video_output = tk.StringVar(
            value="output/video/flyover.mp4"
        )

        self.camera_distance_scale = tk.DoubleVar(value=0.40)
        self.camera_height_scale = tk.DoubleVar(value=0.20)
        self.camera_min_distance = tk.DoubleVar(value=1200.0)
        self.camera_max_distance = tk.DoubleVar(value=3600.0)
        self.camera_min_height = tk.DoubleVar(value=600.0)
        self.camera_max_height = tk.DoubleVar(value=1900.0)
        self.camera_lateral_scale = tk.DoubleVar(value=0.12)
        self.camera_lateral_min = tk.DoubleVar(value=160.0)
        self.camera_lateral_max = tk.DoubleVar(value=700.0)

        self.track_line_width = tk.DoubleVar(value=1.5)
        self.track_z_offset = tk.DoubleVar(value=8.0)
        self.track_progressive = tk.BooleanVar(value=True)
        self.leader_enabled = tk.BooleanVar(value=False)

        self.start_hold = tk.DoubleVar(value=3.0)
        self.arrival_hold = tk.DoubleVar(value=5.0)
        self.profile_duration = tk.DoubleVar(value=6.0)

        self.copernicus_max_cells = tk.IntVar(value=60000)
        self.use_satellite = tk.BooleanVar(value=True)

        self.status_text = tk.StringVar(value="Prêt.")

        self.build_ui()

        if DEFAULT_PROJECT.exists():
            self.load_project(DEFAULT_PROJECT)

    def build_ui(self):
        root = ttk.Frame(self, padding=12)
        root.pack(fill="both", expand=True)

        project_box = ttk.LabelFrame(root, text="Projet", padding=10)
        project_box.pack(fill="x", pady=(0, 10))

        self.add_path_row(
            project_box,
            0,
            "Projet YAML",
            self.project_file,
            self.choose_project,
        )

        self.add_path_row(
            project_box,
            1,
            "Fichier GPX",
            self.gpx_file,
            self.choose_gpx,
        )

        self.add_entry_row(
            project_box,
            2,
            "Titre",
            self.project_title,
        )

        notebook = ttk.Notebook(root)
        notebook.pack(fill="both", expand=True)

        video_tab = ttk.Frame(notebook, padding=12)
        camera_tab = ttk.Frame(notebook, padding=12)
        track_tab = ttk.Frame(notebook, padding=12)
        outro_tab = ttk.Frame(notebook, padding=12)
        terrain_tab = ttk.Frame(notebook, padding=12)

        notebook.add(video_tab, text="Vidéo")
        notebook.add(camera_tab, text="Caméra")
        notebook.add(track_tab, text="Trace")
        notebook.add(outro_tab, text="Départ / arrivée / profil")
        notebook.add(terrain_tab, text="Terrain")

        self.add_entry_row(
            video_tab,
            0,
            "Durée du parcours (s)",
            self.video_duration,
        )

        self.add_entry_row(
            video_tab,
            1,
            "FPS",
            self.video_fps,
        )

        self.add_combo_row(
            video_tab,
            2,
            "Résolution",
            self.video_size,
            ("854x480", "1280x720", "1920x1080"),
        )

        self.add_entry_row(
            video_tab,
            3,
            "Fichier de sortie",
            self.video_output,
        )

        camera_rows = (
            ("Échelle distance", self.camera_distance_scale),
            ("Échelle hauteur", self.camera_height_scale),
            ("Distance minimale", self.camera_min_distance),
            ("Distance maximale", self.camera_max_distance),
            ("Hauteur minimale", self.camera_min_height),
            ("Hauteur maximale", self.camera_max_height),
            ("Échelle latérale", self.camera_lateral_scale),
            ("Latéral minimum", self.camera_lateral_min),
            ("Latéral maximum", self.camera_lateral_max),
        )

        for row, (label, variable) in enumerate(camera_rows):
            self.add_entry_row(camera_tab, row, label, variable)

        self.add_entry_row(
            track_tab,
            0,
            "Largeur de ligne (px)",
            self.track_line_width,
        )

        self.add_entry_row(
            track_tab,
            1,
            "Hauteur au-dessus du terrain (m)",
            self.track_z_offset,
        )

        ttk.Checkbutton(
            track_tab,
            text="Trace progressive",
            variable=self.track_progressive,
        ).grid(row=2, column=0, columnspan=2, sticky="w", pady=6)

        ttk.Checkbutton(
            track_tab,
            text="Leader lumineux",
            variable=self.leader_enabled,
        ).grid(row=3, column=0, columnspan=2, sticky="w", pady=6)

        self.add_entry_row(
            outro_tab,
            0,
            "Pause au départ (s)",
            self.start_hold,
        )

        self.add_entry_row(
            outro_tab,
            1,
            "Pause à l'arrivée (s)",
            self.arrival_hold,
        )

        self.add_entry_row(
            outro_tab,
            2,
            "Durée du profil final (s)",
            self.profile_duration,
        )

        ttk.Checkbutton(
            terrain_tab,
            text="Utiliser le satellite",
            variable=self.use_satellite,
        ).grid(row=0, column=0, columnspan=2, sticky="w", pady=6)

        self.add_entry_row(
            terrain_tab,
            1,
            "Cellules maximales Copernicus",
            self.copernicus_max_cells,
        )

        buttons = ttk.Frame(root)
        buttons.pack(fill="x", pady=(10, 0))

        ttk.Button(
            buttons,
            text="Charger",
            command=self.load_selected_project,
        ).pack(side="left")

        ttk.Button(
            buttons,
            text="Enregistrer",
            command=self.save_project,
        ).pack(side="left", padx=8)

        ttk.Button(
            buttons,
            text="Générer la vidéo",
            command=lambda: self.run_project("VIDEO"),
        ).pack(side="right")

        ttk.Button(
            buttons,
            text="Prévisualiser",
            command=lambda: self.run_project("PREVIEW"),
        ).pack(side="right", padx=8)

        ttk.Label(
            root,
            textvariable=self.status_text,
            anchor="w",
        ).pack(fill="x", pady=(8, 0))

    @staticmethod
    def add_entry_row(parent, row, label, variable):
        ttk.Label(parent, text=label).grid(
            row=row,
            column=0,
            sticky="w",
            padx=(0, 12),
            pady=5,
        )

        ttk.Entry(parent, textvariable=variable).grid(
            row=row,
            column=1,
            sticky="ew",
            pady=5,
        )

        parent.columnconfigure(1, weight=1)

    @staticmethod
    def add_combo_row(parent, row, label, variable, values):
        ttk.Label(parent, text=label).grid(
            row=row,
            column=0,
            sticky="w",
            padx=(0, 12),
            pady=5,
        )

        ttk.Combobox(
            parent,
            textvariable=variable,
            values=values,
            state="readonly",
        ).grid(
            row=row,
            column=1,
            sticky="ew",
            pady=5,
        )

        parent.columnconfigure(1, weight=1)

    @staticmethod
    def add_path_row(parent, row, label, variable, command):
        ttk.Label(parent, text=label).grid(
            row=row,
            column=0,
            sticky="w",
            padx=(0, 8),
            pady=4,
        )

        ttk.Entry(parent, textvariable=variable).grid(
            row=row,
            column=1,
            sticky="ew",
            pady=4,
        )

        ttk.Button(
            parent,
            text="Parcourir",
            command=command,
        ).grid(
            row=row,
            column=2,
            padx=(8, 0),
            pady=4,
        )

        parent.columnconfigure(1, weight=1)

    def choose_project(self):
        filename = filedialog.askopenfilename(
            title="Choisir un projet YAML",
            filetypes=[("Projet YAML", "*.yaml *.yml")],
        )

        if filename:
            self.project_file.set(filename)

    def choose_gpx(self):
        filename = filedialog.askopenfilename(
            title="Choisir un GPX",
            filetypes=[("Fichier GPX", "*.gpx")],
        )

        if filename:
            self.gpx_file.set(filename)

    def load_selected_project(self):
        self.load_project(Path(self.project_file.get()))

    def load_project(self, path):
        if not path.exists():
            messagebox.showerror(
                "Erreur",
                f"Projet introuvable :\n{path}",
            )
            return

        data = yaml.safe_load(
            path.read_text(encoding="utf-8")
        ) or {}

        project = data.get("project", {})
        gpx = data.get("gpx", {})
        video = data.get("video", {})
        camera = data.get("camera", {})
        track = data.get("track", {})
        leader = data.get("leader", {})
        terrain = data.get("terrain", {})
        outro = data.get("outro", {})

        self.project_file.set(str(path))
        self.project_title.set(
            str(project.get("title", "GPX Flyover Studio"))
        )
        self.gpx_file.set(str(gpx.get("file", "")))
        self.video_duration.set(int(video.get("duration", 30)))
        self.video_fps.set(int(video.get("fps", 20)))
        self.video_size.set(str(video.get("size", "1280x720")))
        self.video_output.set(
            str(video.get("output", "output/video/flyover.mp4"))
        )

        self.camera_distance_scale.set(
            float(camera.get("local_fit_distance_scale", 0.40))
        )
        self.camera_height_scale.set(
            float(camera.get("local_fit_height_scale", 0.20))
        )
        self.camera_min_distance.set(
            float(camera.get("local_fit_min_distance", 1200.0))
        )
        self.camera_max_distance.set(
            float(camera.get("local_fit_max_distance", 3600.0))
        )
        self.camera_min_height.set(
            float(camera.get("local_fit_min_height", 600.0))
        )
        self.camera_max_height.set(
            float(camera.get("local_fit_max_height", 1900.0))
        )
        self.camera_lateral_scale.set(
            float(camera.get("lateral_distance_scale", 0.12))
        )
        self.camera_lateral_min.set(
            float(camera.get("lateral_minimum", 160.0))
        )
        self.camera_lateral_max.set(
            float(camera.get("lateral_maximum", 700.0))
        )

        self.track_line_width.set(
            float(track.get("line_width", 1.5))
        )
        self.track_z_offset.set(
            float(track.get("z_offset", 8.0))
        )
        self.track_progressive.set(
            bool(track.get("progressive", True))
        )
        self.leader_enabled.set(
            bool(leader.get("enabled", False))
        )

        self.start_hold.set(
            float(outro.get("start_hold_seconds", 3.0))
        )
        self.arrival_hold.set(
            float(outro.get("arrival_hold_seconds", 5.0))
        )
        self.profile_duration.set(
            float(outro.get("profile_seconds", 6.0))
        )

        self.copernicus_max_cells.set(
            int(terrain.get("copernicus_max_cells", 60000))
        )
        self.use_satellite.set(
            bool(terrain.get("use_satellite", True))
        )

        self.status_text.set(f"Projet chargé : {path}")

    def project_data(self, mode):
        return {
            "project": {
                "title": self.project_title.get(),
            },
            "gpx": {
                "file": self.gpx_file.get(),
            },
            "video": {
                "mode": mode,
                "duration": int(self.video_duration.get()),
                "final_hold_seconds": 0,
                "fps": int(self.video_fps.get()),
                "size": self.video_size.get(),
                "output": self.video_output.get(),
            },
            "camera": {
                "mode": "director",
                "preset": "cinematic",
                "orientation": {
                    "mode": "auto",
                },
                "local_fit_distance_scale": float(
                    self.camera_distance_scale.get()
                ),
                "local_fit_height_scale": float(
                    self.camera_height_scale.get()
                ),
                "local_fit_min_distance": float(
                    self.camera_min_distance.get()
                ),
                "local_fit_max_distance": float(
                    self.camera_max_distance.get()
                ),
                "local_fit_min_height": float(
                    self.camera_min_height.get()
                ),
                "local_fit_max_height": float(
                    self.camera_max_height.get()
                ),
                "lateral_distance_scale": float(
                    self.camera_lateral_scale.get()
                ),
                "lateral_minimum": float(
                    self.camera_lateral_min.get()
                ),
                "lateral_maximum": float(
                    self.camera_lateral_max.get()
                ),
            },
            "track": {
                "render_mode": "line",
                "progressive": bool(
                    self.track_progressive.get()
                ),
                "update_every": 6,
                "line_width": float(
                    self.track_line_width.get()
                ),
                "z_offset": float(
                    self.track_z_offset.get()
                ),
            },
            "leader": {
                "enabled": bool(
                    self.leader_enabled.get()
                ),
            },
            "terrain": {
                "source": "copernicus",
                "copernicus_max_cells": int(
                    self.copernicus_max_cells.get()
                ),
                "use_satellite": bool(
                    self.use_satellite.get()
                ),
            },
            "outro": {
                "start_hold_seconds": float(
                    self.start_hold.get()
                ),
                "arrival_hold_seconds": float(
                    self.arrival_hold.get()
                ),
                "profile_seconds": float(
                    self.profile_duration.get()
                ),
            },
            "timeline": [],
        }

    def save_project(self, mode=None):
        path = Path(self.project_file.get())

        if not path.suffix:
            path = path.with_suffix(".yaml")
            self.project_file.set(str(path))

        path.parent.mkdir(parents=True, exist_ok=True)

        selected_mode = mode or "PREVIEW"

        path.write_text(
            yaml.safe_dump(
                self.project_data(selected_mode),
                allow_unicode=True,
                sort_keys=False,
            ),
            encoding="utf-8",
        )

        self.status_text.set(f"Projet enregistré : {path}")

        return path

    def run_project(self, mode):
        try:
            project_file = self.save_project(mode)
            subprocess.Popen(
                [
                    sys.executable,
                    "main.py",
                    "project",
                    str(project_file),
                ],
                cwd=Path.cwd(),
            )
            self.status_text.set(
                f"{mode} lancé avec {project_file}"
            )
        except Exception as error:
            messagebox.showerror(
                "Erreur",
                str(error),
            )


if __name__ == "__main__":
    app = FlyoverStudioGUI()
    app.mainloop()
