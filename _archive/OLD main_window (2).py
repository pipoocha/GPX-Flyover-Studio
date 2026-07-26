from __future__ import annotations

import subprocess
import sys
import tkinter as tk
from pathlib import Path
from tkinter import colorchooser, filedialog, messagebox, ttk

from studio.config.loader import ProjectLoaderV5
from studio.config.models import CameraRange
from studio.config.validator import validate_project


class HelpRow(ttk.Frame):
    def __init__(
        self,
        parent,
        *,
        label: str,
        help_text: str,
        variable: tk.Variable,
        unit: str = "",
        values: tuple[str, ...] | None = None,
        from_: float | None = None,
        to: float | None = None,
        resolution: float = 1.0,
    ):
        super().__init__(parent)

        self.variable = variable
        self.columnconfigure(1, weight=1)

        ttk.Label(
            self,
            text=label,
            width=30,
        ).grid(
            row=0,
            column=0,
            sticky="w",
            padx=(0, 10),
        )

        if values is not None:
            widget = ttk.Combobox(
                self,
                textvariable=variable,
                values=values,
                state="readonly",
                width=20,
            )
        elif from_ is not None and to is not None:
            widget = ttk.Scale(
                self,
                variable=variable,
                from_=from_,
                to=to,
                orient="horizontal",
            )
        else:
            widget = ttk.Entry(
                self,
                textvariable=variable,
            )

        widget.grid(
            row=0,
            column=1,
            sticky="ew",
        )

        value_label = ttk.Label(
            self,
            width=12,
            anchor="e",
        )

        value_label.grid(
            row=0,
            column=2,
            padx=(10, 0),
        )

        def refresh_value(*_):
            value = variable.get()

            if isinstance(value, float):
                if resolution >= 1:
                    display = f"{value:.0f}"
                elif resolution >= 0.1:
                    display = f"{value:.1f}"
                else:
                    display = f"{value:.2f}"
            else:
                display = str(value)

            value_label.configure(
                text=f"{display} {unit}".strip()
            )

        variable.trace_add(
            "write",
            refresh_value,
        )

        refresh_value()

        ttk.Label(
            self,
            text=help_text,
            foreground="#666666",
            wraplength=620,
            justify="left",
        ).grid(
            row=1,
            column=0,
            columnspan=3,
            sticky="w",
            pady=(2, 8),
        )


class MainWindow(tk.Tk):
    def __init__(self):
        super().__init__()

        self.title("GPX Flyover Studio V5.2")
        self.geometry("980x820")
        self.minsize(900, 720)

        self.project = None
        self.project_file = tk.StringVar(
            value="projects/project_v5.yaml"
        )

        self.status_text = tk.StringVar(
            value="Prêt."
        )

        self.vars: dict[str, tk.Variable] = {}

        self._create_variables()
        self._build_ui()

        default_project = Path(
            self.project_file.get()
        )

        if default_project.exists():
            self.load_project(
                default_project
            )

    def _create_variables(self):
        self.vars = {
            "title": tk.StringVar(),
            "gpx": tk.StringVar(),

            "camera_mode": tk.StringVar(
                value="director"
            ),
            "orientation": tk.StringVar(
                value="auto"
            ),

            "distance_min": tk.DoubleVar(
                value=1200
            ),
            "distance_max": tk.DoubleVar(
                value=3600
            ),
            "distance_scale": tk.DoubleVar(
                value=0.40
            ),

            "height_min": tk.DoubleVar(
                value=600
            ),
            "height_max": tk.DoubleVar(
                value=1900
            ),
            "height_scale": tk.DoubleVar(
                value=0.20
            ),

            "lateral_min": tk.DoubleVar(
                value=160
            ),
            "lateral_max": tk.DoubleVar(
                value=700
            ),
            "lateral_scale": tk.DoubleVar(
                value=0.12
            ),

            "look_ahead": tk.IntVar(
                value=260
            ),
            "smoothing": tk.DoubleVar(
                value=0.10
            ),

            "track_color": tk.StringVar(
                value="#FC4C02"
            ),
            "track_width": tk.DoubleVar(
                value=1.5
            ),
            "track_z": tk.DoubleVar(
                value=8.0
            ),
            "track_progressive": tk.BooleanVar(
                value=True
            ),
            "track_leader": tk.BooleanVar(
                value=False
            ),

            "terrain_source": tk.StringVar(
                value="copernicus"
            ),
            "terrain_satellite": tk.BooleanVar(
                value=True
            ),
            "terrain_zoom": tk.IntVar(
                value=14
            ),
            "terrain_max_cells": tk.IntVar(
                value=60000
            ),
            "terrain_margin": tk.DoubleVar(
                value=0.006
            ),

            "intro": tk.DoubleVar(
                value=2.0
            ),
            "zoom_to_start": tk.DoubleVar(
                value=2.0
            ),
            "start_hold": tk.DoubleVar(
                value=3.0
            ),
            "travel": tk.DoubleVar(
                value=30.0
            ),
            "slowdown_start": tk.DoubleVar(
                value=2.0
            ),
            "slowdown_end": tk.DoubleVar(
                value=3.0
            ),
            "arrival_hold": tk.DoubleVar(
                value=5.0
            ),
            "flatten": tk.DoubleVar(
                value=3.0
            ),
            "profile_animation": tk.DoubleVar(
                value=6.0
            ),
            "profile_hold": tk.DoubleVar(
                value=4.0
            ),
            "fade_out": tk.DoubleVar(
                value=2.0
            ),

            "fps": tk.IntVar(
                value=20
            ),
            "resolution": tk.StringVar(
                value="1280x720"
            ),
            "output": tk.StringVar(
                value="output/video/flyover_v5.mp4"
            ),
        }

    def _build_ui(self):
        root = ttk.Frame(
            self,
            padding=12,
        )

        root.pack(
            fill="both",
            expand=True,
        )

        project_box = ttk.LabelFrame(
            root,
            text="Projet",
            padding=10,
        )

        project_box.pack(
            fill="x",
            pady=(0, 10),
        )

        project_box.columnconfigure(
            1,
            weight=1,
        )

        ttk.Label(
            project_box,
            text="Projet YAML",
        ).grid(
            row=0,
            column=0,
            sticky="w",
            padx=(0, 10),
            pady=4,
        )

        ttk.Entry(
            project_box,
            textvariable=self.project_file,
        ).grid(
            row=0,
            column=1,
            sticky="ew",
            pady=4,
        )

        ttk.Button(
            project_box,
            text="Ouvrir...",
            command=self.choose_project,
        ).grid(
            row=0,
            column=2,
            padx=(8, 0),
        )

        ttk.Label(
            project_box,
            text="Titre du projet",
        ).grid(
            row=1,
            column=0,
            sticky="w",
            padx=(0, 10),
            pady=4,
        )

        ttk.Entry(
            project_box,
            textvariable=self.vars["title"],
        ).grid(
            row=1,
            column=1,
            sticky="ew",
            pady=4,
        )

        ttk.Label(
            project_box,
            text="Fichier GPX",
        ).grid(
            row=2,
            column=0,
            sticky="w",
            padx=(0, 10),
            pady=4,
        )

        ttk.Entry(
            project_box,
            textvariable=self.vars["gpx"],
        ).grid(
            row=2,
            column=1,
            sticky="ew",
            pady=4,
        )

        ttk.Button(
            project_box,
            text="Parcourir...",
            command=self.choose_gpx,
        ).grid(
            row=2,
            column=2,
            padx=(8, 0),
        )

        notebook = ttk.Notebook(
            root
        )

        notebook.pack(
            fill="both",
            expand=True,
        )

        camera_tab = self._scrollable_tab(
            notebook,
            "Caméra",
        )

        terrain_tab = self._scrollable_tab(
            notebook,
            "Terrain",
        )

        track_tab = self._scrollable_tab(
            notebook,
            "Trace",
        )

        timeline_tab = self._scrollable_tab(
            notebook,
            "Timeline",
        )

        video_tab = self._scrollable_tab(
            notebook,
            "Vidéo",
        )

        self._build_camera_tab(
            camera_tab
        )

        self._build_terrain_tab(
            terrain_tab
        )

        self._build_track_tab(
            track_tab
        )

        self._build_timeline_tab(
            timeline_tab
        )

        self._build_video_tab(
            video_tab
        )

        actions = ttk.Frame(
            root
        )

        actions.pack(
            fill="x",
            pady=(10, 0),
        )

        ttk.Button(
            actions,
            text="Réinitialiser",
            command=self.reset_defaults,
        ).pack(
            side="left",
        )

        ttk.Button(
            actions,
            text="Enregistrer",
            command=self.save_project,
        ).pack(
            side="left",
            padx=8,
        )

        ttk.Button(
            actions,
            text="Prévisualiser",
            command=lambda: self.run_project(
                "PREVIEW"
            ),
        ).pack(
            side="right",
            padx=(8, 0),
        )

        ttk.Button(
            actions,
            text="Générer la vidéo",
            command=lambda: self.run_project(
                "VIDEO"
            ),
        ).pack(
            side="right",
        )

        ttk.Label(
            root,
            textvariable=self.status_text,
            anchor="w",
        ).pack(
            fill="x",
            pady=(8, 0),
        )

    def _scrollable_tab(
        self,
        notebook,
        title,
    ):
        container = ttk.Frame(
            notebook
        )

        notebook.add(
            container,
            text=title,
        )

        canvas = tk.Canvas(
            container,
            highlightthickness=0,
        )

        scrollbar = ttk.Scrollbar(
            container,
            orient="vertical",
            command=canvas.yview,
        )

        inner = ttk.Frame(
            canvas,
            padding=12,
        )

        inner.bind(
            "<Configure>",
            lambda event: canvas.configure(
                scrollregion=canvas.bbox(
                    "all"
                )
            ),
        )

        canvas.create_window(
            (0, 0),
            window=inner,
            anchor="nw",
        )

        canvas.configure(
            yscrollcommand=scrollbar.set
        )

        canvas.pack(
            side="left",
            fill="both",
            expand=True,
        )

        scrollbar.pack(
            side="right",
            fill="y",
        )

        return inner

    def _add_help_row(
        self,
        parent,
        *,
        label,
        help_text,
        key,
        unit="",
        values=None,
        from_=None,
        to=None,
        resolution=1.0,
    ):
        row = HelpRow(
            parent,
            label=label,
            help_text=help_text,
            variable=self.vars[key],
            unit=unit,
            values=values,
            from_=from_,
            to=to,
            resolution=resolution,
        )

        row.pack(
            fill="x",
            pady=2,
        )

    def _build_camera_tab(
        self,
        parent,
    ):
        self._add_help_row(
            parent,
            label="Mode caméra",
            help_text=(
                "Director suit automatiquement la trace. "
                "C'est le mode conseillé pour les vidéos."
            ),
            key="camera_mode",
            values=(
                "director",
                "flyover",
                "stage",
            ),
        )

        self._add_help_row(
            parent,
            label="Orientation",
            help_text=(
                "Auto suit la direction générale. "
                "North conserve le nord en haut."
            ),
            key="orientation",
            values=(
                "auto",
                "route",
                "north",
                "fixed",
            ),
        )

        self._add_help_row(
            parent,
            label="Distance minimale",
            help_text=(
                "Distance la plus proche entre la caméra et la trace. "
                "Réduire cette valeur rapproche le suivi."
            ),
            key="distance_min",
            unit="m",
            from_=300,
            to=4000,
        )

        self._add_help_row(
            parent,
            label="Distance maximale",
            help_text=(
                "Distance maximale utilisée dans les zones ouvertes "
                "ou lorsque le relief est important."
            ),
            key="distance_max",
            unit="m",
            from_=800,
            to=8000,
        )

        self._add_help_row(
            parent,
            label="Échelle de distance",
            help_text=(
                "Influence de la taille totale du parcours sur le recul. "
                "Valeur conseillée : 0,25 à 0,45."
            ),
            key="distance_scale",
            from_=0.10,
            to=0.80,
            resolution=0.01,
        )

        self._add_help_row(
            parent,
            label="Hauteur minimale",
            help_text=(
                "Hauteur minimale de la caméra au-dessus de la trace."
            ),
            key="height_min",
            unit="m",
            from_=100,
            to=2500,
        )

        self._add_help_row(
            parent,
            label="Hauteur maximale",
            help_text=(
                "Hauteur maximale autorisée lorsque le relief augmente."
            ),
            key="height_max",
            unit="m",
            from_=400,
            to=5000,
        )

        self._add_help_row(
            parent,
            label="Échelle de hauteur",
            help_text=(
                "Influence de la taille du parcours sur la hauteur caméra. "
                "Valeur conseillée : 0,10 à 0,25."
            ),
            key="height_scale",
            from_=0.05,
            to=0.60,
            resolution=0.01,
        )

        self._add_help_row(
            parent,
            label="Décalage latéral minimal",
            help_text=(
                "Décalage horizontal minimal. "
                "Une petite valeur réduit l'effet de rotation."
            ),
            key="lateral_min",
            unit="m",
            from_=0,
            to=1000,
        )

        self._add_help_row(
            parent,
            label="Décalage latéral maximal",
            help_text=(
                "Décalage horizontal maximal. "
                "Réduire cette valeur stabilise le terrain."
            ),
            key="lateral_max",
            unit="m",
            from_=50,
            to=2500,
        )

        self._add_help_row(
            parent,
            label="Échelle latérale",
            help_text=(
                "Part de la distance utilisée pour placer la caméra "
                "sur le côté de la trace."
            ),
            key="lateral_scale",
            from_=0.00,
            to=0.40,
            resolution=0.01,
        )

        self._add_help_row(
            parent,
            label="Anticipation",
            help_text=(
                "Nombre de points regardés devant la position actuelle. "
                "Une valeur trop élevée augmente les rotations."
            ),
            key="look_ahead",
            from_=20,
            to=600,
        )

        self._add_help_row(
            parent,
            label="Lissage",
            help_text=(
                "Fluidité de la caméra. "
                "Une valeur faible ralentit les changements."
            ),
            key="smoothing",
            from_=0.02,
            to=0.30,
            resolution=0.01,
        )

    def _build_terrain_tab(
        self,
        parent,
    ):
        self._add_help_row(
            parent,
            label="Source de relief",
            help_text=(
                "Copernicus est recommandé pour la haute montagne."
            ),
            key="terrain_source",
            values=(
                "copernicus",
                "srtm",
            ),
        )

        ttk.Checkbutton(
            parent,
            text="Afficher la texture satellite",
            variable=self.vars[
                "terrain_satellite"
            ],
        ).pack(
            anchor="w",
            pady=(4, 2),
        )

        ttk.Label(
            parent,
            text=(
                "Décochez cette option pour tester rapidement "
                "le relief sans téléchargement satellite."
            ),
            foreground="#666666",
            wraplength=620,
        ).pack(
            anchor="w",
            pady=(0, 10),
        )

        self._add_help_row(
            parent,
            label="Zoom satellite",
            help_text=(
                "14 convient à la plupart des treks. "
                "15 ou 16 augmente la qualité mais aussi la taille."
            ),
            key="terrain_zoom",
            from_=10,
            to=18,
        )

        self._add_help_row(
            parent,
            label="Cellules maximales",
            help_text=(
                "Nombre maximal de cellules du relief. "
                "60 000 est rapide ; 150 000 donne plus de détails."
            ),
            key="terrain_max_cells",
            from_=30000,
            to=250000,
        )

        self._add_help_row(
            parent,
            label="Marge du terrain",
            help_text=(
                "Zone ajoutée autour de la trace. "
                "Augmenter cette valeur rend les bords moins visibles."
            ),
            key="terrain_margin",
            from_=0.002,
            to=0.050,
            resolution=0.001,
        )

    def _build_track_tab(
        self,
        parent,
    ):
        color_frame = ttk.Frame(
            parent
        )

        color_frame.pack(
            fill="x",
            pady=4,
        )

        ttk.Label(
            color_frame,
            text="Couleur de la trace",
            width=30,
        ).pack(
            side="left",
        )

        ttk.Entry(
            color_frame,
            textvariable=self.vars[
                "track_color"
            ],
        ).pack(
            side="left",
            fill="x",
            expand=True,
        )

        ttk.Button(
            color_frame,
            text="Choisir...",
            command=self.choose_color,
        ).pack(
            side="left",
            padx=(8, 0),
        )

        ttk.Label(
            parent,
            text=(
                "Couleur au format #RRGGBB. "
                "Exemple : #FC4C02 pour l'orange Strava."
            ),
            foreground="#666666",
            wraplength=620,
        ).pack(
            anchor="w",
            pady=(0, 10),
        )

        self._add_help_row(
            parent,
            label="Largeur",
            help_text=(
                "Épaisseur à l'écran en pixels. "
                "1 à 2 px est conseillé."
            ),
            key="track_width",
            unit="px",
            from_=0.5,
            to=10.0,
            resolution=0.1,
        )

        self._add_help_row(
            parent,
            label="Décalage vertical",
            help_text=(
                "Relève la trace au-dessus du terrain "
                "pour éviter qu'elle disparaisse."
            ),
            key="track_z",
            unit="m",
            from_=0,
            to=50,
        )

        ttk.Checkbutton(
            parent,
            text="Trace progressive",
            variable=self.vars[
                "track_progressive"
            ],
        ).pack(
            anchor="w",
            pady=4,
        )

        ttk.Checkbutton(
            parent,
            text="Leader lumineux",
            variable=self.vars[
                "track_leader"
            ],
        ).pack(
            anchor="w",
            pady=4,
        )

    def _build_timeline_tab(
        self,
        parent,
    ):
        rows = (
            (
                "Intro",
                "intro",
                "Vue générale avant le rapprochement.",
            ),
            (
                "Zoom vers le départ",
                "zoom_to_start",
                "Durée du mouvement vers le premier point.",
            ),
            (
                "Pause départ",
                "start_hold",
                "Temps immobile sur le début de la trace.",
            ),
            (
                "Parcours",
                "travel",
                "Durée du déplacement principal.",
            ),
            (
                "Ralentissement départ",
                "slowdown_start",
                "Accélération progressive au début.",
            ),
            (
                "Ralentissement arrivée",
                "slowdown_end",
                "Décélération progressive avant l'arrivée.",
            ),
            (
                "Pause arrivée",
                "arrival_hold",
                "Temps immobile sur le dernier point.",
            ),
            (
                "Mise à plat",
                "flatten",
                "Transition finale vers la vue générale.",
            ),
            (
                "Animation du profil",
                "profile_animation",
                "Durée du dessin animé du profil.",
            ),
            (
                "Maintien du profil",
                "profile_hold",
                "Temps pendant lequel le profil reste affiché.",
            ),
            (
                "Fondu final",
                "fade_out",
                "Durée du fondu noir.",
            ),
        )

        for label, key, help_text in rows:
            self._add_help_row(
                parent,
                label=label,
                help_text=help_text,
                key=key,
                unit="s",
                from_=0,
                to=60,
                resolution=0.5,
            )

    def _build_video_tab(
        self,
        parent,
    ):
        self._add_help_row(
            parent,
            label="Images par seconde",
            help_text=(
                "20 FPS est rapide. "
                "30 FPS donne un mouvement plus fluide."
            ),
            key="fps",
            unit="FPS",
            from_=10,
            to=60,
        )

        self._add_help_row(
            parent,
            label="Résolution",
            help_text=(
                "1280x720 pour les tests ; "
                "1920x1080 pour la vidéo finale."
            ),
            key="resolution",
            values=(
                "854x480",
                "1280x720",
                "1920x1080",
                "2560x1440",
                "3840x2160",
            ),
        )

        self._add_help_row(
            parent,
            label="Fichier de sortie",
            help_text=(
                "Chemin du fichier MP4 généré."
            ),
            key="output",
        )

    def choose_project(self):
        filename = filedialog.askopenfilename(
            title="Choisir un projet YAML",
            filetypes=[
                (
                    "Projet YAML",
                    "*.yaml *.yml",
                )
            ],
        )

        if filename:
            self.project_file.set(
                filename
            )

            self.load_project(
                Path(filename)
            )

    def choose_gpx(self):
        filename = filedialog.askopenfilename(
            title="Choisir un fichier GPX",
            filetypes=[
                (
                    "Fichier GPX",
                    "*.gpx",
                )
            ],
        )

        if filename:
            self.vars["gpx"].set(
                filename
            )

    def choose_color(self):
        selected = colorchooser.askcolor(
            color=self.vars[
                "track_color"
            ].get()
        )[1]

        if selected:
            self.vars[
                "track_color"
            ].set(
                selected.upper()
            )

    def load_project(
        self,
        project_file,
    ):
        try:
            self.project = ProjectLoaderV5(
                project_file
            ).load()

            self.project_file.set(
                str(project_file)
            )

            self._fill_form()

            self.status_text.set(
                f"Projet chargé : {project_file}"
            )

        except Exception as error:
            messagebox.showerror(
                "Erreur",
                str(error),
            )

    def _fill_form(self):
        project = self.project

        values = {
            "title": project.title,
            "gpx": project.gpx.file,
            "camera_mode": project.camera.mode,
            "orientation": project.camera.orientation,

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
            "track_progressive": project.track.progressive,
            "track_leader": project.track.leader,

            "terrain_source": project.terrain.source,
            "terrain_satellite": project.terrain.satellite,
            "terrain_zoom": project.terrain.satellite_zoom,
            "terrain_max_cells": project.terrain.max_cells,
            "terrain_margin": project.terrain.margin,

            "fps": project.video.fps,
            "resolution": project.video.resolution,
            "output": project.video.output,
        }

        values.update(
            project.timeline.to_dict()
        )

        for key, value in values.items():
            if key in self.vars:
                self.vars[key].set(
                    value
                )

    def _update_project_from_form(
        self,
        mode=None,
    ):
        if self.project is None:
            self.project = ProjectLoaderV5(
                self.project_file.get()
            ).load()

        project = self.project

        project.title = str(
            self.vars["title"].get()
        )

        project.gpx.file = Path(
            self.vars["gpx"].get()
        )

        project.camera.mode = str(
            self.vars[
                "camera_mode"
            ].get()
        )

        project.camera.orientation = str(
            self.vars[
                "orientation"
            ].get()
        )

        project.camera.distance = CameraRange(
            minimum=float(
                self.vars[
                    "distance_min"
                ].get()
            ),
            maximum=float(
                self.vars[
                    "distance_max"
                ].get()
            ),
            scale=float(
                self.vars[
                    "distance_scale"
                ].get()
            ),
        )

        project.camera.height = CameraRange(
            minimum=float(
                self.vars[
                    "height_min"
                ].get()
            ),
            maximum=float(
                self.vars[
                    "height_max"
                ].get()
            ),
            scale=float(
                self.vars[
                    "height_scale"
                ].get()
            ),
        )

        project.camera.lateral = CameraRange(
            minimum=float(
                self.vars[
                    "lateral_min"
                ].get()
            ),
            maximum=float(
                self.vars[
                    "lateral_max"
                ].get()
            ),
            scale=float(
                self.vars[
                    "lateral_scale"
                ].get()
            ),
        )

        project.camera.look_ahead = int(
            self.vars[
                "look_ahead"
            ].get()
        )

        project.camera.smoothing = float(
            self.vars[
                "smoothing"
            ].get()
        )

        project.track.color = str(
            self.vars[
                "track_color"
            ].get()
        )

        project.track.width = float(
            self.vars[
                "track_width"
            ].get()
        )

        project.track.z_offset = float(
            self.vars[
                "track_z"
            ].get()
        )

        project.track.progressive = bool(
            self.vars[
                "track_progressive"
            ].get()
        )

        project.track.leader = bool(
            self.vars[
                "track_leader"
            ].get()
        )

        project.terrain.source = str(
            self.vars[
                "terrain_source"
            ].get()
        )

        project.terrain.satellite = bool(
            self.vars[
                "terrain_satellite"
            ].get()
        )

        project.terrain.satellite_zoom = int(
            self.vars[
                "terrain_zoom"
            ].get()
        )

        project.terrain.max_cells = int(
            self.vars[
                "terrain_max_cells"
            ].get()
        )

        project.terrain.margin = float(
            self.vars[
                "terrain_margin"
            ].get()
        )

        for key in project.timeline.to_dict():
            setattr(
                project.timeline,
                key,
                float(
                    self.vars[key].get()
                ),
            )

        project.video.fps = int(
            self.vars["fps"].get()
        )

        width, height = (
            ProjectLoaderV5
            .parse_resolution(
                self.vars[
                    "resolution"
                ].get()
            )
        )

        project.video.width = width
        project.video.height = height

        project.video.output = Path(
            self.vars["output"].get()
        )

        if mode:
            project.video.mode = mode

        validate_project(
            project
        )

    def save_project(self):
        try:
            self._update_project_from_form()

            path = ProjectLoaderV5.save(
                self.project,
                self.project_file.get(),
            )

            self.status_text.set(
                f"Projet enregistré : {path}"
            )

        except Exception as error:
            messagebox.showerror(
                "Erreur",
                str(error),
            )

    def run_project(
        self,
        mode,
    ):
        try:
            self._update_project_from_form(
                mode=mode
            )

            path = ProjectLoaderV5.save(
                self.project,
                self.project_file.get(),
            )

            subprocess.Popen(
                [
                    sys.executable,
                    "main.py",
                    "project",
                    str(path),
                    "--mode",
                    mode,
                ],
                cwd=Path.cwd(),
            )

            self.status_text.set(
                f"{mode} lancé."
            )

        except Exception as error:
            messagebox.showerror(
                "Erreur",
                str(error),
            )

    def reset_defaults(self):
        try:
            default_project = ProjectLoaderV5(
                self.project_file.get()
            ).load()

            self.project = default_project
            self._fill_form()

            self.status_text.set(
                "Valeurs rechargées depuis le YAML."
            )

        except Exception as error:
            messagebox.showerror(
                "Erreur",
                str(error),
            )


if __name__ == "__main__":
    MainWindow().mainloop()
