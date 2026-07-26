from __future__ import annotations

import subprocess
import sys
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

from studio.analyzer import analyze_gpx
from studio.config.loader import ProjectLoaderV5
from studio.profiles import ProfileManager


class V6WelcomeWindow(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("GPX Flyover Studio V6")
        self.geometry("980x760")
        self.minsize(900, 680)

        self.gpx_path = tk.StringVar()
        self.project_path = tk.StringVar()
        self.project_title = tk.StringVar()
        self.terrain_profile = tk.StringVar()
        self.style_profile = tk.StringVar()
        self.quality_profile = tk.StringVar()
        self.duration_profile = tk.IntVar(value=60)
        self.analysis = None
        self.analysis_vars = {
            key: tk.StringVar(value="—")
            for key in (
                "points",
                "distance",
                "elevation",
                "gain",
                "loss",
                "relief",
                "difficulty",
                "zone",
            )
        }
        self.status_text = tk.StringVar(value="Choisissez un GPX pour commencer.")
        self._build_ui()

    def _build_ui(self):
        root = ttk.Frame(self, padding=16)
        root.pack(fill="both", expand=True)

        ttk.Label(root, text="GPX FLYOVER STUDIO V6", font=("Segoe UI", 22, "bold")).pack(anchor="w")
        ttk.Label(
            root,
            text="Choisissez un GPX. Le logiciel analyse le parcours et prépare automatiquement les réglages.",
            foreground="#555555",
        ).pack(anchor="w", pady=(2, 14))

        source = ttk.LabelFrame(root, text="1 — Parcours", padding=12)
        source.pack(fill="x")
        source.columnconfigure(1, weight=1)

        self._entry_row(source, 0, "Fichier GPX", self.gpx_path)
        ttk.Button(source, text="Parcourir...", command=self.choose_gpx).grid(row=0, column=2, padx=(8, 0))
        self._entry_row(source, 1, "Titre du projet", self.project_title)
        self._entry_row(source, 2, "Projet YAML", self.project_path)
        ttk.Button(source, text="Choisir...", command=self.choose_project_path).grid(row=2, column=2, padx=(8, 0))
        ttk.Button(source, text="Analyser le GPX", command=self.analyze_selected_gpx).grid(row=3, column=1, sticky="e", pady=(10, 0))

        middle = ttk.Frame(root)
        middle.pack(fill="both", expand=True, pady=12)
        analysis_box = ttk.LabelFrame(middle, text="2 — Analyse", padding=12)
        analysis_box.pack(side="left", fill="both", expand=True, padx=(0, 6))

        rows = (
            ("Points", "points"),
            ("Distance", "distance"),
            ("Altitude", "elevation"),
            ("Dénivelé positif", "gain"),
            ("Dénivelé négatif", "loss"),
            ("Indice de relief", "relief"),
            ("Difficulté", "difficulty"),
            ("Zone couverte", "zone"),
        )
        for row, (label, key) in enumerate(rows):
            ttk.Label(analysis_box, text=label).grid(row=row, column=0, sticky="w", padx=(0, 18), pady=5)
            ttk.Label(analysis_box, textvariable=self.analysis_vars[key], font=("Segoe UI", 10, "bold")).grid(row=row, column=1, sticky="w", pady=5)

        profile_box = ttk.LabelFrame(middle, text="3 — Profil proposé", padding=12)
        profile_box.pack(side="left", fill="both", expand=True, padx=(6, 0))
        profile_box.columnconfigure(1, weight=1)
        self._combo_row(profile_box, 0, "Terrain", self.terrain_profile, ("Plaine", "Collines", "Moyenne montagne", "Haute montagne", "Himalaya"))
        self._combo_row(profile_box, 1, "Style", self.style_profile, ("Drone", "Tour de France", "Hélicoptère", "Cinéma", "Director"))
        self._combo_row(profile_box, 2, "Qualité", self.quality_profile, ("Rapide", "Standard", "Haute", "Ultra"))

        ttk.Label(profile_box, text="Durée du parcours").grid(row=3, column=0, sticky="w", padx=(0, 10), pady=7)
        frame = ttk.Frame(profile_box)
        frame.grid(row=3, column=1, sticky="ew", pady=7)
        frame.columnconfigure(0, weight=1)
        ttk.Scale(frame, variable=self.duration_profile, from_=20, to=300, orient="horizontal").grid(row=0, column=0, sticky="ew")
        ttk.Label(frame, textvariable=self.duration_profile, width=5, anchor="e").grid(row=0, column=1, padx=(8, 0))
        ttk.Label(frame, text="s").grid(row=0, column=2)

        actions = ttk.Frame(root)
        actions.pack(fill="x")
        ttk.Button(actions, text="Créer et ouvrir l'éditeur", command=self.create_and_open_editor).pack(side="right")
        ttk.Button(actions, text="Créer puis prévisualiser", command=self.create_and_preview).pack(side="right", padx=(0, 8))
        ttk.Label(root, textvariable=self.status_text, anchor="w").pack(fill="x", pady=(10, 0))

    @staticmethod
    def _entry_row(parent, row, label, variable):
        ttk.Label(parent, text=label).grid(row=row, column=0, sticky="w", padx=(0, 10), pady=4)
        ttk.Entry(parent, textvariable=variable).grid(row=row, column=1, sticky="ew", pady=4)

    @staticmethod
    def _combo_row(parent, row, label, variable, values):
        ttk.Label(parent, text=label).grid(row=row, column=0, sticky="w", padx=(0, 10), pady=7)
        ttk.Combobox(parent, textvariable=variable, values=values, state="readonly").grid(row=row, column=1, sticky="ew", pady=7)

    def choose_gpx(self):
        filename = filedialog.askopenfilename(title="Choisir un GPX", filetypes=[("Fichier GPX", "*.gpx")])
        if not filename:
            return
        gpx = Path(filename)
        self.gpx_path.set(str(gpx))
        self.project_title.set(gpx.stem.replace("_", " "))
        self.project_path.set(str(Path("projects") / f"{gpx.stem}.yaml"))
        self.analyze_selected_gpx()

    def choose_project_path(self):
        filename = filedialog.asksaveasfilename(
            title="Enregistrer le projet",
            initialdir="projects",
            initialfile=f"{Path(self.gpx_path.get()).stem or 'nouveau_projet'}.yaml",
            defaultextension=".yaml",
            filetypes=[("Projet YAML", "*.yaml")],
        )
        if filename:
            self.project_path.set(filename)

    def analyze_selected_gpx(self):
        try:
            gpx = Path(self.gpx_path.get().strip())
            if not gpx.is_file():
                raise FileNotFoundError("Sélectionnez un fichier GPX valide.")
            self.status_text.set("Analyse du GPX...")
            self.update_idletasks()
            self.analysis = analyze_gpx(gpx)
            suggested = ProfileManager.suggest(self.analysis)
            self.analysis_vars["points"].set(str(self.analysis.point_count))
            self.analysis_vars["distance"].set(f"{self.analysis.distance_km:.1f} km")
            self.analysis_vars["elevation"].set(f"{self.analysis.min_elevation_m:.0f} → {self.analysis.max_elevation_m:.0f} m")
            self.analysis_vars["gain"].set(f"{self.analysis.ascent_m:.0f} m")
            self.analysis_vars["loss"].set(f"{self.analysis.descent_m:.0f} m")
            self.analysis_vars["relief"].set(f"{self.analysis.relief_index}/100 — {self.analysis.terrain_profile}")
            self.analysis_vars["difficulty"].set(f"{self.analysis.difficulty_index}/100 — {self.analysis.difficulty_label}")
            self.analysis_vars["zone"].set(f"{self.analysis.bbox_width_km:.1f} × {self.analysis.bbox_height_km:.1f} km")
            self.terrain_profile.set(suggested.terrain)
            self.style_profile.set(suggested.style)
            self.quality_profile.set(suggested.quality)
            self.duration_profile.set(suggested.duration_seconds)
            self.status_text.set("Analyse terminée. Modifiez le profil si nécessaire.")
        except Exception as error:
            messagebox.showerror("Analyse GPX", str(error))
            self.status_text.set("Échec de l'analyse.")

    def _build_project(self):
        if self.analysis is None:
            self.analyze_selected_gpx()
        if self.analysis is None:
            raise RuntimeError("Analyse GPX non disponible.")
        template_path = Path("projects/project_v5.yaml")
        if not template_path.exists():
            raise FileNotFoundError("Le modèle projects/project_v5.yaml est introuvable.")
        project = ProjectLoaderV5(template_path).load()
        project.title = self.project_title.get().strip() or self.analysis.name
        project.gpx.file = Path(self.gpx_path.get())
        ProfileManager.apply_to_project(
            project,
            terrain=self.terrain_profile.get(),
            style=self.style_profile.get(),
            quality=self.quality_profile.get(),
            duration_seconds=int(self.duration_profile.get()),
        )
        project_path = Path(self.project_path.get())
        if not project_path.suffix:
            project_path = project_path.with_suffix(".yaml")
            self.project_path.set(str(project_path))
        project.video.output = Path("output/video") / f"{project_path.stem}.mp4"
        ProjectLoaderV5.save(project, project_path)
        return project_path

    def create_and_open_editor(self):
        try:
            project_path = self._build_project()
            subprocess.Popen([sys.executable, "-m", "studio.gui.main_window", str(project_path)], cwd=Path.cwd())
            self.status_text.set(f"Projet créé : {project_path}")
        except Exception as error:
            messagebox.showerror("Création du projet", str(error))

    def create_and_preview(self):
        try:
            project_path = self._build_project()
            subprocess.Popen([sys.executable, "main.py", "project", str(project_path), "--mode", "PREVIEW"], cwd=Path.cwd())
            self.status_text.set(f"Preview lancé : {project_path}")
        except Exception as error:
            messagebox.showerror("Prévisualisation", str(error))


if __name__ == "__main__":
    V6WelcomeWindow().mainloop()
