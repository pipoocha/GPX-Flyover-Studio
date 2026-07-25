from __future__ import annotations

import subprocess
import sys
import tkinter as tk
from pathlib import Path
from tkinter import colorchooser, filedialog, messagebox, ttk

from studio.config.loader import ProjectLoaderV5
from studio.config.models import CameraRange
from studio.config.validator import validate_project


class MainWindow(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("GPX Flyover Studio V5")
        self.geometry("920x780")
        self.project = None
        self.project_file = tk.StringVar(value="projects/project_v5.yaml")
        self.vars: dict[str, tk.StringVar] = {}
        self.build_ui()

    def build_ui(self):
        root = ttk.Frame(self, padding=12)
        root.pack(fill="both", expand=True)

        top = ttk.Frame(root)
        top.pack(fill="x")

        ttk.Entry(top, textvariable=self.project_file).pack(
            side="left", fill="x", expand=True
        )
        ttk.Button(top, text="Ouvrir", command=self.open_project).pack(
            side="left", padx=6
        )
        ttk.Button(top, text="Enregistrer", command=self.save_project).pack(
            side="left"
        )

        notebook = ttk.Notebook(root)
        notebook.pack(fill="both", expand=True, pady=10)

        tabs = {
            "project": ttk.Frame(notebook, padding=12),
            "camera": ttk.Frame(notebook, padding=12),
            "track": ttk.Frame(notebook, padding=12),
            "timeline": ttk.Frame(notebook, padding=12),
            "video": ttk.Frame(notebook, padding=12),
        }

        notebook.add(tabs["project"], text="Projet")
        notebook.add(tabs["camera"], text="Caméra")
        notebook.add(tabs["track"], text="Trace")
        notebook.add(tabs["timeline"], text="Timeline")
        notebook.add(tabs["video"], text="Vidéo")

        self.entry(tabs["project"], 0, "Titre", "title")
        self.entry(tabs["project"], 1, "Fichier GPX", "gpx")
        ttk.Button(
            tabs["project"], text="Parcourir...", command=self.choose_gpx
        ).grid(row=1, column=2, padx=6)

        camera_rows = (
            ("Distance min", "distance_min"),
            ("Distance max", "distance_max"),
            ("Échelle distance", "distance_scale"),
            ("Hauteur min", "height_min"),
            ("Hauteur max", "height_max"),
            ("Échelle hauteur", "height_scale"),
            ("Latéral min", "lateral_min"),
            ("Latéral max", "lateral_max"),
            ("Échelle latérale", "lateral_scale"),
            ("Anticipation", "look_ahead"),
            ("Lissage", "smoothing"),
        )
        for row, (label, key) in enumerate(camera_rows):
            self.entry(tabs["camera"], row, label, key)

        self.entry(tabs["track"], 0, "Couleur", "track_color", "#FC4C02")
        self.entry(tabs["track"], 1, "Largeur", "track_width", "1.5")
        self.entry(tabs["track"], 2, "Décalage Z", "track_z", "8.0")
        ttk.Button(
            tabs["track"], text="Choisir la couleur", command=self.choose_color
        ).grid(row=0, column=2, padx=6)

        timeline_rows = (
            ("Intro", "intro"),
            ("Zoom départ", "zoom_to_start"),
            ("Pause départ", "start_hold"),
            ("Parcours", "travel"),
            ("Ralentissement départ", "slowdown_start"),
            ("Ralentissement arrivée", "slowdown_end"),
            ("Pause arrivée", "arrival_hold"),
            ("Mise à plat", "flatten"),
            ("Animation profil", "profile_animation"),
            ("Maintien profil", "profile_hold"),
            ("Fondu", "fade_out"),
        )
        for row, (label, key) in enumerate(timeline_rows):
            self.entry(tabs["timeline"], row, label, key)

        self.entry(tabs["video"], 0, "FPS", "fps", "20")
        self.entry(tabs["video"], 1, "Résolution", "resolution", "1280x720")
        self.entry(
            tabs["video"],
            2,
            "Sortie",
            "output",
            "output/video/flyover_v5.mp4",
        )

        actions = ttk.Frame(root)
        actions.pack(fill="x")
        ttk.Button(
            actions,
            text="Générer la vidéo",
            command=lambda: self.run_project("VIDEO"),
        ).pack(side="right")
        ttk.Button(
            actions,
            text="Prévisualiser",
            command=lambda: self.run_project("PREVIEW"),
        ).pack(side="right", padx=6)

    def entry(self, parent, row, label, key, default=""):
        variable = tk.StringVar(value=str(default))
        self.vars[key] = variable
        ttk.Label(parent, text=label).grid(
            row=row, column=0, sticky="w", padx=(0, 12), pady=5
        )
        ttk.Entry(parent, textvariable=variable).grid(
            row=row, column=1, sticky="ew", pady=5
        )
        parent.columnconfigure(1, weight=1)

    def choose_gpx(self):
        value = filedialog.askopenfilename(filetypes=[("GPX", "*.gpx")])
        if value:
            self.vars["gpx"].set(value)

    def choose_color(self):
        value = colorchooser.askcolor(
            color=self.vars["track_color"].get()
        )[1]
        if value:
            self.vars["track_color"].set(value.upper())

    def open_project(self):
        value = filedialog.askopenfilename(
            filetypes=[("YAML", "*.yaml *.yml")]
        )
        if not value:
            return
        self.project_file.set(value)
        try:
            self.project = ProjectLoaderV5(value).load()
            self.fill_form()
        except Exception as error:
            messagebox.showerror("Erreur", str(error))

    def fill_form(self):
        project = self.project
        values = {
            "title": project.title,
            "gpx": project.gpx.file,
            "distance_min": project.camera.distance.minimum,
            "distance_max": project.camera.distance.maximum,
            "distance_scale": project.camera.distance.scale,
            "height_min": project.camera.height.minimum,
            "height_max": project.camera.height.maximum,
            "height_scale": project.camera.height.scale,
            "lateral_min": project.camera.lateral.minimum,
            "lateral_max": project.camera.lateral.maximum,
            "lateral_scale": project.camera.lateral.scale,
            "look_ahead": project.camera.look_ahead,
            "smoothing": project.camera.smoothing,
            "track_color": project.track.color,
            "track_width": project.track.width,
            "track_z": project.track.z_offset,
            "fps": project.video.fps,
            "resolution": project.video.resolution,
            "output": project.video.output,
        }
        values.update(project.timeline.to_dict())
        for key, value in values.items():
            if key in self.vars:
                self.vars[key].set(str(value))

    def update_project_from_form(self, mode=None):
        if self.project is None:
            self.project = ProjectLoaderV5(self.project_file.get()).load()

        self.project.title = self.vars["title"].get()
        self.project.gpx.file = Path(self.vars["gpx"].get())
        self.project.camera.distance = CameraRange(
            float(self.vars["distance_min"].get()),
            float(self.vars["distance_max"].get()),
            float(self.vars["distance_scale"].get()),
        )
        self.project.camera.height = CameraRange(
            float(self.vars["height_min"].get()),
            float(self.vars["height_max"].get()),
            float(self.vars["height_scale"].get()),
        )
        self.project.camera.lateral = CameraRange(
            float(self.vars["lateral_min"].get()),
            float(self.vars["lateral_max"].get()),
            float(self.vars["lateral_scale"].get()),
        )
        self.project.camera.look_ahead = int(self.vars["look_ahead"].get())
        self.project.camera.smoothing = float(self.vars["smoothing"].get())
        self.project.track.color = self.vars["track_color"].get()
        self.project.track.width = float(self.vars["track_width"].get())
        self.project.track.z_offset = float(self.vars["track_z"].get())

        for key in self.project.timeline.to_dict():
            setattr(self.project.timeline, key, float(self.vars[key].get()))

        self.project.video.fps = int(self.vars["fps"].get())
        width, height = ProjectLoaderV5.parse_resolution(
            self.vars["resolution"].get()
        )
        self.project.video.width = width
        self.project.video.height = height
        self.project.video.output = Path(self.vars["output"].get())
        if mode:
            self.project.video.mode = mode
        validate_project(self.project)

    def save_project(self):
        try:
            self.update_project_from_form()
            ProjectLoaderV5.save(self.project, self.project_file.get())
            messagebox.showinfo("V5", "Projet enregistré.")
        except Exception as error:
            messagebox.showerror("Erreur", str(error))

    def run_project(self, mode):
        try:
            self.update_project_from_form(mode=mode)
            project_file = ProjectLoaderV5.save(
                self.project, self.project_file.get()
            )
            subprocess.Popen(
                [sys.executable, "main.py", "project", str(project_file)],
                cwd=Path.cwd(),
            )
        except Exception as error:
            messagebox.showerror("Erreur", str(error))


if __name__ == "__main__":
    MainWindow().mainloop()
