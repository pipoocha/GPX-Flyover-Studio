from __future__ import annotations

import subprocess
import sys
import tkinter as tk
from pathlib import Path
from tkinter import colorchooser, filedialog, messagebox, simpledialog, ttk

from studio.config.loader import ProjectLoaderV5
from studio.config.models import CameraRange
from studio.analysis.analyzer import analyze_gpx
from studio.profiles.engine import ProfileEngine
from studio.config.validator import validate_project
from studio.profiles import ProfileManager


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
        advisor=None,
    ):
        super().__init__(parent)

        self.variable = variable
        self.advisor = advisor
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
                length=500,
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

        if values is None and from_ is not None and to is not None:
            value_label = ttk.Spinbox(
                self,
                textvariable=variable,
                from_=from_,
                to=to,
                increment=resolution,
                width=10,
            )
        else:
            value_label = ttk.Label(
                self,
                width=16,
                anchor="e",
            )

        value_label.grid(
            row=0,
            column=2,
            padx=(10, 0),
        )

        def refresh_value(*_):
            try:
                value = variable.get()
            except (tk.TclError, ValueError):
                if isinstance(value_label, ttk.Label):
                    value_label.configure(text="")
                return

            if isinstance(value, float):
                if resolution >= 1:
                    display = f"{value:.0f}"
                elif resolution >= 0.1:
                    display = f"{value:.1f}"
                else:
                    display = f"{value:.2f}"
            else:
                display = str(value)

            if isinstance(value_label, ttk.Label):
                value_label.configure(
                    text=f"{display} {unit}".strip()
                )

            if self.advisor is not None:
                try:
                    self.help_label.configure(
                        text=self.advisor(value)
                    )
                except Exception:
                    self.help_label.configure(
                        text=help_text
                    )

        self.help_label = ttk.Label(
            self,
            text=help_text,
            foreground="#666666",
            wraplength=620,
            justify="left",
        )
        self.help_label.grid(
            row=1,
            column=0,
            columnspan=3,
            sticky="w",
            pady=(2, 8),
        )

        variable.trace_add(
            "write",
            refresh_value,
        )

        refresh_value()


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

        self.status_text.set(
            "Choisissez un fichier GPX pour ouvrir ou créer son projet."
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

            "leader_enabled": tk.BooleanVar(
                value=False
            ),
            "leader_style": tk.StringVar(
                value="glow"
            ),
            "leader_color": tk.StringVar(
                value="#FC4C02"
            ),
            "leader_radius": tk.DoubleVar(
                value=20.0
            ),
            "profile_marker_radius": tk.DoubleVar(
                value=10.0
            ),
            "leader_z_offset": tk.DoubleVar(
                value=18.0
            ),
            "leader_halo_scale": tk.DoubleVar(
                value=1.8
            ),
            "leader_halo_opacity": tk.DoubleVar(
                value=0.20
            ),
            "leader_trail_enabled": tk.BooleanVar(
                value=True
            ),
            "leader_trail_fraction": tk.DoubleVar(
                value=0.035
            ),
            "leader_trail_width": tk.DoubleVar(
                value=10.0
            ),
            "leader_trail_opacity": tk.DoubleVar(
                value=0.55
            ),
            "leader_fade_trail_on_arrival": tk.BooleanVar(
                value=True
            ),
            "leader_trail_fade_duration": tk.DoubleVar(
                value=1.5
            ),
            "leader_screen_space": tk.BooleanVar(
                value=True
            ),

            "cinematic_start_centered": tk.BooleanVar(
                value=True
            ),
            "cinematic_start_zoom": tk.DoubleVar(
                value=0.45
            ),
            "cinematic_start_transition": tk.DoubleVar(
                value=3.0
            ),
            "cinematic_finish_zoom": tk.DoubleVar(
                value=0.70
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

            "progress_speed": tk.DoubleVar(
                value=1.0
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
            "profile_terrain": tk.StringVar(value="Moyenne montagne"),
            "profile_style": tk.StringVar(value="Tour de France"),
            "profile_quality": tk.StringVar(value="Standard"),
            "user_profile": tk.StringVar(value=""),
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

        ttk.Label(project_box, text="Fichier GPX").grid(
            row=0, column=0, sticky="w", padx=(0, 10), pady=4
        )
        ttk.Entry(
            project_box,
            textvariable=self.vars["gpx"],
        ).grid(
            row=0, column=1, sticky="ew", pady=4
        )
        ttk.Button(
            project_box,
            text="Choisir un GPX...",
            command=self.choose_gpx,
        ).grid(
            row=0, column=2, padx=(8, 0)
        )

        ttk.Label(project_box, text="Titre du projet").grid(
            row=1, column=0, sticky="w", padx=(0, 10), pady=4
        )
        ttk.Entry(
            project_box,
            textvariable=self.vars["title"],
        ).grid(
            row=1, column=1, sticky="ew", pady=4
        )

        ttk.Label(project_box, text="Projet associé").grid(
            row=2, column=0, sticky="w", padx=(0, 10), pady=4
        )
        ttk.Label(
            project_box,
            textvariable=self.project_file,
            foreground="#666666",
        ).grid(
            row=2, column=1, sticky="w", pady=4
        )
        ttk.Button(
            project_box,
            text="Ouvrir un YAML...",
            command=self.choose_project,
        ).grid(
            row=2, column=2, padx=(8, 0)
        )

        profile_box = ttk.LabelFrame(root, text="Profils de rendu", padding=10)
        profile_box.pack(fill="x", pady=(0, 10))
        for column in (1, 3, 5):
            profile_box.columnconfigure(column, weight=1)

        ttk.Label(profile_box, text="Terrain").grid(row=0,column=0,sticky="w",padx=(0,6))
        ttk.Combobox(profile_box,textvariable=self.vars["profile_terrain"],values=tuple(ProfileManager.TERRAIN_PROFILES),state="readonly",width=22).grid(row=0,column=1,sticky="ew",padx=(0,14))
        ttk.Label(profile_box, text="Style").grid(row=0,column=2,sticky="w",padx=(0,6))
        ttk.Combobox(profile_box,textvariable=self.vars["profile_style"],values=tuple(ProfileManager.STYLE_PROFILES),state="readonly",width=20).grid(row=0,column=3,sticky="ew",padx=(0,14))
        ttk.Label(profile_box, text="Qualité").grid(row=0,column=4,sticky="w",padx=(0,6))
        ttk.Combobox(profile_box,textvariable=self.vars["profile_quality"],values=tuple(ProfileManager.QUALITY_PROFILES),state="readonly",width=14).grid(row=0,column=5,sticky="ew",padx=(0,14))
        ttk.Button(profile_box,text="Appliquer les profils",command=self.apply_selected_profiles).grid(row=0,column=6,padx=(8,0))

        ttk.Separator(profile_box,orient="horizontal").grid(row=1,column=0,columnspan=7,sticky="ew",pady=10)
        ttk.Label(profile_box,text="Mes profils").grid(row=2,column=0,sticky="w",padx=(0,6))
        self.user_profile_combo=ttk.Combobox(profile_box,textvariable=self.vars["user_profile"],state="readonly",width=28)
        self.user_profile_combo.grid(row=2,column=1,columnspan=2,sticky="ew",padx=(0,14))
        ttk.Button(profile_box,text="Charger",command=self.load_user_profile).grid(row=2,column=3,padx=(0,6))
        ttk.Button(profile_box,text="Enregistrer sous...",command=self.save_user_profile_as).grid(row=2,column=4,padx=(0,6))
        ttk.Button(profile_box,text="Mettre à jour",command=self.update_user_profile).grid(row=2,column=5,padx=(0,6))
        ttk.Button(profile_box,text="Supprimer",command=self.delete_user_profile).grid(row=2,column=6)
        self.user_profile_description=ttk.Label(profile_box,text="Aucun profil personnel sélectionné.",foreground="#666666",wraplength=860,justify="left")
        self.user_profile_description.grid(row=3,column=0,columnspan=7,sticky="w",pady=(7,0))
        self.user_profile_combo.bind("<<ComboboxSelected>>",self.show_user_profile_description)
        self.refresh_user_profiles()

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

        realization_tab = self._scrollable_tab(
            notebook,
            "Réalisation",
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

        self._build_realization_tab(
            realization_tab
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
        advisor=None,
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
            advisor=advisor,
        )

        row.pack(
            fill="x",
            pady=2,
        )

    @staticmethod
    def _stars(value):
        value = max(1, min(5, int(round(value))))
        return "★" * value + "☆" * (5 - value)

    def advise_distance_min(self, value):
        value = float(value)
        if value < 700:
            return (
                "Caméra très proche : immersion maximale, mais le paysage "
                "peut être coupé dans les vallées étroites.\n"
                f"Immersion {self._stars(5)}  Vue générale {self._stars(2)}"
            )
        if value < 1500:
            return (
                "Réglage conseillé pour le trek : suivi proche et relief lisible.\n"
                f"Immersion {self._stars(4)}  Vue générale {self._stars(4)}"
            )
        if value < 2600:
            return (
                "Vue aérienne équilibrée : davantage de paysage, trace plus petite.\n"
                f"Immersion {self._stars(3)}  Vue générale {self._stars(5)}"
            )
        return (
            "Caméra très éloignée : utile dans les grandes vallées, "
            "mais la trace devient discrète.\n"
            f"Immersion {self._stars(2)}  Vue générale {self._stars(5)}"
        )

    def advise_distance_max(self, value):
        value = float(value)
        if value < 2200:
            return "Recul limité : effet drone et terrain stable."
        if value < 4200:
            return "Plage équilibrée : conseillée pour la haute montagne."
        return "Grand recul : plus de paysage, mais risque d'effet de plaque."

    def advise_distance_scale(self, value):
        value = float(value)
        if value < 0.22:
            return "Faible : la caméra reste proche, même sur les longs GPX."
        if value < 0.46:
            return "Bon compromis : adaptation naturelle à la taille du parcours."
        return "Élevée : recul important sur les grands itinéraires."

    def advise_height_min(self, value):
        value = float(value)
        if value < 350:
            return "Très bas : effet drone spectaculaire, sensible au relief."
        if value < 850:
            return "Hauteur immersive conseillée pour un trek."
        if value < 1500:
            return "Vue aérienne large, sensation de vitesse réduite."
        return "Vue panoramique haute, proche d'une carte 3D."

    def advise_height_max(self, value):
        value = float(value)
        if value < 1200:
            return "Hauteur contenue : rendu proche et dynamique."
        if value < 2400:
            return "Plage recommandée pour les reliefs himalayens."
        return "Très haute : utile pour les sommets, mais rendu plus lointain."

    def advise_height_scale(self, value):
        value = float(value)
        if value < 0.12:
            return "Faible : la caméra reste basse malgré la longueur du parcours."
        if value < 0.26:
            return "Conseillée : adaptation progressive et naturelle."
        return "Forte : la caméra montera vite sur les grands itinéraires."

    def advise_lateral(self, value):
        value = float(value)
        if value < 100:
            return "Presque dans l'axe : terrain très stable."
        if value < 450:
            return "Décalage modéré recommandé : relief visible sans trop tourner."
        return "Décalage important : vue latérale forte et rotation plus visible."

    def advise_lateral_scale(self, value):
        value = float(value)
        if value < 0.08:
            return "Très stable : caméra presque dans l'axe du parcours."
        if value < 0.18:
            return "Conseillée : légère vue latérale sans rotation excessive."
        return "Très latérale : spectaculaire, mais le terrain tournera davantage."

    def advise_look_ahead(self, value):
        value = int(value)
        if value < 100:
            return "Regard proche : caméra réactive, parfois nerveuse."
        if value < 300:
            return "Conseillé : bonne anticipation et rotations contenues."
        return "Regard lointain : mouvements plus amples et davantage de rotation."

    def advise_smoothing(self, value):
        value = float(value)
        if value < 0.06:
            return "Très doux : mouvements stables, réactions plus lentes."
        if value < 0.14:
            return "Conseillé : fluide tout en restant précis."
        if value < 0.22:
            return "Réactif : suit mieux les virages, mais peut devenir nerveux."
        return "Très réactif : changements rapides, risque de saccades."

    def advise_margin(self, value):
        value = float(value)
        if value < 0.008:
            return "Terrain compact : calcul rapide, bords parfois visibles."
        if value < 0.020:
            return "Conseillée : terrain plus naturel et bords rarement visibles."
        return "Grande emprise : aspect naturel, calcul et texture plus lourds."

    def advise_cells(self, value):
        value = int(value)
        if value < 70000:
            return "Mode rapide : idéal pour le preview."
        if value < 150000:
            return "Qualité standard : bon équilibre détails / performances."
        return "Haute qualité : relief plus fin, rendu nettement plus long."

    def advise_track_width(self, value):
        value = float(value)
        if value <= 1.2:
            return "Trace très fine et discrète."
        if value <= 2.2:
            return "Largeur recommandée : visible sans effet de ver."
        return "Trace épaisse : très visible, mais moins naturelle."

    def advise_fps(self, value):
        value = int(value)
        if value <= 20:
            return "Rapide à calculer, fluidité correcte pour les tests."
        if value <= 30:
            return "Réglage conseillé pour la vidéo finale."
        return "Très fluide, mais rendu et fichier plus lourds."

    def advise_camera_mode(self, value):
        value = str(value).lower()

        if value == "director":
            return (
                "🟢 Recommandé — Suit automatiquement la trace avec un cadrage "
                "stable et cinématographique. Idéal pour les treks."
            )

        if value == "flyover":
            return (
                "🟠 Correct — Caméra plus libre et plus dynamique. "
                "Montre davantage le paysage, mais peut tourner davantage."
            )

        if value == "stage":
            return (
                "🟠 Présentation — Vue plus statique, adaptée aux étapes "
                "et aux plans de démonstration."
            )

        return "Mode caméra personnalisé."

    def advise_orientation(self, value):
        value = str(value).lower()

        if value == "auto":
            return (
                "🟢 Recommandé — L'orientation suit naturellement le parcours "
                "sans imposer une direction fixe."
            )

        if value == "route":
            return (
                "🟢 Suivi de trace — La caméra reste alignée avec la direction "
                "du parcours. Bon compromis pour un trek."
            )

        if value == "north":
            return (
                "🟠 Cartographique — Le nord reste prioritaire. "
                "Le terrain paraît plus stable mais moins cinématographique."
            )

        if value == "fixed":
            return (
                "🟠 Fixe — Orientation constante. Très stable, mais moins adaptée "
                "aux parcours sinueux."
            )

        return "Orientation personnalisée."

    def advise_terrain_source(self, value):
        value = str(value).lower()

        if value == "copernicus":
            return (
                "🟢 Recommandé — Relief plus propre et plus fiable en haute montagne. "
                "Idéal pour Himalaya, Alpes et Pyrénées."
            )

        if value == "srtm":
            return (
                "🟠 Plus léger — Calcul souvent plus rapide, mais relief moins propre "
                "dans les zones très escarpées."
            )

        return "Source de relief personnalisée."

    def advise_resolution(self, value):
        value = str(value).lower()

        if value == "854x480":
            return (
                "🟢 Test rapide — Très adapté aux previews. "
                "Temps de calcul minimal."
            )

        if value == "1280x720":
            return (
                "🟢 Recommandé pour les essais — Bonne lisibilité et rendu encore rapide."
            )

        if value == "1920x1080":
            return (
                "🟢 Full HD — Réglage conseillé pour la vidéo finale. "
                "Temps de rendu environ 2 à 3 fois supérieur au 720p."
            )

        if value == "2560x1440":
            return (
                "🟠 Haute définition — Image plus fine, rendu nettement plus long."
            )

        if value == "3840x2160":
            return (
                "🔴 4K — Très grande qualité, mais calcul et fichier beaucoup plus lourds. "
                "À réserver à l'export final."
            )

        return "Résolution personnalisée."

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
            advisor=self.advise_camera_mode,
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
            advisor=self.advise_orientation,
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
            advisor=self.advise_distance_min,
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
            advisor=self.advise_distance_max,
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
            advisor=self.advise_distance_scale,
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
            advisor=self.advise_height_min,
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
            advisor=self.advise_height_max,
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
            advisor=self.advise_height_scale,
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
            advisor=self.advise_lateral,
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
            advisor=self.advise_lateral,
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
            advisor=self.advise_lateral_scale,
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
            advisor=self.advise_look_ahead,
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
            advisor=self.advise_smoothing,
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
            advisor=self.advise_terrain_source,
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
            advisor=self.advise_cells,
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
            advisor=self.advise_margin,
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
            advisor=self.advise_track_width,
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

        ttk.Separator(
            parent,
            orient="horizontal",
        ).pack(
            fill="x",
            pady=(12, 10),
        )

        ttk.Label(
            parent,
            text="Leader lumineux",
            font=("Segoe UI", 11, "bold"),
        ).pack(
            anchor="w",
            pady=(0, 6),
        )

        ttk.Checkbutton(
            parent,
            text="Activer le leader",
            variable=self.vars[
                "leader_enabled"
            ],
        ).pack(
            anchor="w",
            pady=4,
        )

        self._add_help_row(
            parent,
            label="Style",
            help_text=(
                "Point : marqueur seul. Glow : point avec halo. "
                "Comet : point, halo et traînée."
            ),
            key="leader_style",
            values=(
                "point",
                "glow",
                "comet",
            ),
        )

        leader_color_frame = ttk.Frame(
            parent
        )

        leader_color_frame.pack(
            fill="x",
            pady=4,
        )

        ttk.Label(
            leader_color_frame,
            text="Couleur du leader",
            width=30,
        ).pack(
            side="left",
        )

        self.leader_color_swatch = tk.Canvas(
            leader_color_frame,
            width=34,
            height=22,
            highlightthickness=1,
            highlightbackground="#777777",
        )
        self.leader_color_swatch.pack(
            side="left",
            padx=(0, 8),
        )

        ttk.Entry(
            leader_color_frame,
            textvariable=self.vars[
                "leader_color"
            ],
            width=14,
        ).pack(
            side="left",
            fill="x",
            expand=True,
        )

        ttk.Button(
            leader_color_frame,
            text="Choisir...",
            command=self.choose_leader_color,
        ).pack(
            side="left",
            padx=(8, 0),
        )

        self._add_help_row(
            parent,
            label="Taille du point",
            help_text=(
                "Rayon du cœur lumineux. Augmentez-le si le leader "
                "est trop discret avec une caméra éloignée."
            ),
            key="leader_radius",
            unit="m",
            from_=2,
            to=60,
            resolution=1,
        )

        self._add_help_row(
            parent,
            label="Taille du point sur la carte finale",
            help_text=(
                "Taille du point mobile affiché sur le terrain pendant "
                "l’animation finale du profil. Ce réglage est indépendant "
                "du leader principal."
            ),
            key="profile_marker_radius",
            unit="m",
            from_=3,
            to=40,
            resolution=1,
        )

        self._add_help_row(
            parent,
            label="Hauteur du leader",
            help_text=(
                "Distance verticale entre le leader et la trace."
            ),
            key="leader_z_offset",
            unit="m",
            from_=0,
            to=60,
            resolution=1,
        )

        ttk.Label(
            parent,
            text="Halo",
            font=("Segoe UI", 10, "bold"),
        ).pack(
            anchor="w",
            pady=(10, 2),
        )

        self._add_help_row(
            parent,
            label="Taille du halo",
            help_text=(
                "Multiplicateur appliqué à la taille du point."
            ),
            key="leader_halo_scale",
            from_=1.0,
            to=4.0,
            resolution=0.1,
        )

        self._add_help_row(
            parent,
            label="Intensité du halo",
            help_text=(
                "Opacité du halo : 0 le rend invisible, 1 le rend opaque."
            ),
            key="leader_halo_opacity",
            from_=0.0,
            to=1.0,
            resolution=0.05,
        )

        ttk.Label(
            parent,
            text="Traînée",
            font=("Segoe UI", 10, "bold"),
        ).pack(
            anchor="w",
            pady=(10, 2),
        )

        ttk.Checkbutton(
            parent,
            text="Afficher la traînée",
            variable=self.vars[
                "leader_trail_enabled"
            ],
        ).pack(
            anchor="w",
            pady=4,
        )

        self._add_help_row(
            parent,
            label="Longueur de traînée",
            help_text=(
                "Fraction du parcours conservée derrière le leader. "
                "0,035 correspond à environ 3,5 % du parcours."
            ),
            key="leader_trail_fraction",
            from_=0.0,
            to=0.15,
            resolution=0.005,
        )

        self._add_help_row(
            parent,
            label="Largeur de traînée",
            help_text=(
                "Épaisseur de la traînée lumineuse."
            ),
            key="leader_trail_width",
            unit="px",
            from_=1,
            to=30,
            resolution=1,
        )

        self._add_help_row(
            parent,
            label="Opacité de traînée",
            help_text=(
                "Transparence de la traînée."
            ),
            key="leader_trail_opacity",
            from_=0.0,
            to=1.0,
            resolution=0.05,
        )

        ttk.Checkbutton(
            parent,
            text="Effacer la traînée à l'arrivée",
            variable=self.vars[
                "leader_fade_trail_on_arrival"
            ],
        ).pack(
            anchor="w",
            pady=(8, 4),
        )

        self._add_help_row(
            parent,
            label="Durée d'effacement",
            help_text=(
                "Durée pendant laquelle la traînée se raccourcit "
                "et devient transparente après l'arrivée."
            ),
            key="leader_trail_fade_duration",
            unit="s",
            from_=0.2,
            to=5.0,
            resolution=0.1,
        )

        ttk.Checkbutton(
            parent,
            text="Adapter la taille à la distance caméra",
            variable=self.vars[
                "leader_screen_space"
            ],
        ).pack(
            anchor="w",
            pady=(6, 4),
        )

        ttk.Separator(
            parent,
            orient="horizontal",
        ).pack(
            fill="x",
            pady=(12, 10),
        )

        ttk.Label(
            parent,
            text="Aperçu du leader",
            font=("Segoe UI", 10, "bold"),
        ).pack(
            anchor="w",
            pady=(0, 4),
        )

        self.leader_preview_canvas = tk.Canvas(
            parent,
            width=620,
            height=150,
            background="#202020",
            highlightthickness=1,
            highlightbackground="#555555",
        )
        self.leader_preview_canvas.pack(
            fill="x",
            pady=(0, 8),
        )

        ttk.Label(
            parent,
            text=(
                "Cet aperçu montre la couleur, le style, le halo, "
                "la taille et la traînée sans lancer le moteur 3D."
            ),
            foreground="#666666",
            wraplength=620,
        ).pack(
            anchor="w",
            pady=(0, 6),
        )

        for preview_key in (
            "leader_enabled",
            "leader_style",
            "leader_color",
            "leader_radius",
            "leader_halo_scale",
            "leader_halo_opacity",
            "leader_trail_enabled",
            "leader_trail_fraction",
            "leader_trail_width",
            "leader_trail_opacity",
        ):
            self.vars[preview_key].trace_add(
                "write",
                self._update_leader_preview,
            )

        self._update_leader_preview()

    def _build_realization_tab(
        self,
        parent,
    ):
        start_box = ttk.LabelFrame(
            parent,
            text="Départ",
            padding=12,
        )
        start_box.pack(
            fill="x",
            pady=(0, 12),
        )

        ttk.Checkbutton(
            start_box,
            text="Centrer automatiquement le point de départ",
            variable=self.vars[
                "cinematic_start_centered"
            ],
        ).pack(
            anchor="w",
            pady=(0, 8),
        )

        self._add_help_row(
            start_box,
            label="Zoom de départ",
            help_text=(
                "0,20 donne un très gros plan ; 1,00 conserve "
                "la distance normale de la caméra Director."
            ),
            key="cinematic_start_zoom",
            unit="×",
            from_=0.20,
            to=1.00,
            resolution=0.05,
        )

        self._add_help_row(
            start_box,
            label="Transition vers le suivi",
            help_text=(
                "Durée du passage progressif entre le gros plan "
                "du départ et la caméra normale."
            ),
            key="cinematic_start_transition",
            unit="s",
            from_=0.0,
            to=10.0,
            resolution=0.25,
        )

        self._add_help_row(
            start_box,
            label="Pause au départ",
            help_text=(
                "Le leader reste immobile et centré pendant cette durée."
            ),
            key="start_hold",
            unit="s",
            from_=0.0,
            to=15.0,
            resolution=0.5,
        )

        finish_box = ttk.LabelFrame(
            parent,
            text="Arrivée",
            padding=12,
        )
        finish_box.pack(
            fill="x",
            pady=(0, 12),
        )

        self._add_help_row(
            finish_box,
            label="Zoom d'arrivée",
            help_text=(
                "Valeur inférieure à 1,00 : rapprochement progressif "
                "sur le dernier point. 1,00 conserve le cadrage normal."
            ),
            key="cinematic_finish_zoom",
            unit="×",
            from_=0.30,
            to=1.50,
            resolution=0.05,
        )

        self._add_help_row(
            finish_box,
            label="Pause à l'arrivée",
            help_text=(
                "Durée pendant laquelle le dernier point reste affiché."
            ),
            key="arrival_hold",
            unit="s",
            from_=0.0,
            to=20.0,
            resolution=0.5,
        )

        ttk.Checkbutton(
            finish_box,
            text="Faire disparaître progressivement la traînée",
            variable=self.vars[
                "leader_fade_trail_on_arrival"
            ],
        ).pack(
            anchor="w",
            pady=(8, 4),
        )

        self._add_help_row(
            finish_box,
            label="Durée d'effacement",
            help_text=(
                "Durée de disparition de la traînée après l'arrivée."
            ),
            key="leader_trail_fade_duration",
            unit="s",
            from_=0.2,
            to=5.0,
            resolution=0.1,
        )

        note = ttk.Label(
            parent,
            text=(
                "Ces réglages sont également conservés dans les onglets "
                "techniques actuels pendant la transition vers l'interface V6."
            ),
            foreground="#666666",
            wraplength=760,
            justify="left",
        )
        note.pack(
            anchor="w",
            pady=(2, 8),
        )

    def _build_timeline_tab(
        self,
        parent,
    ):
        self._add_help_row(
            parent,
            label="Vitesse de progression",
            help_text=(
                "1× conserve la vitesse actuelle. 2× avance deux fois plus vite "
                "et divise la durée du parcours par deux. 0,5× ralentit de moitié."
            ),
            key="progress_speed",
            unit="×",
            from_=0.25,
            to=4.0,
            resolution=0.05,
        )

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
            advisor=self.advise_fps,
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
            advisor=self.advise_resolution,
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

    PROFILE_SETTING_KEYS = (
        "camera_mode", "orientation", "distance_min", "distance_max", "distance_scale",
        "height_min", "height_max", "height_scale", "lateral_min", "lateral_max",
        "lateral_scale", "look_ahead", "smoothing", "track_color", "track_width",
        "track_z", "track_progressive", "track_leader",
        "leader_enabled", "leader_style", "leader_color",
        "leader_radius", "profile_marker_radius", "leader_z_offset", "leader_halo_scale",
        "leader_halo_opacity", "leader_trail_enabled",
        "leader_trail_fraction", "leader_trail_width",
        "leader_trail_opacity", "leader_fade_trail_on_arrival",
        "leader_trail_fade_duration", "leader_screen_space",
        "cinematic_start_centered", "cinematic_start_zoom",
        "cinematic_start_transition", "cinematic_finish_zoom",
        "terrain_source",
        "terrain_satellite", "terrain_zoom", "terrain_max_cells", "terrain_margin",
        "progress_speed", "intro", "zoom_to_start", "start_hold", "travel", "slowdown_start",
        "slowdown_end", "arrival_hold", "flatten", "profile_animation",
        "profile_hold", "fade_out", "fps", "resolution",
    )

    def collect_profile_settings(self):
        return {key:self.vars[key].get() for key in self.PROFILE_SETTING_KEYS}

    def apply_profile_settings(self, settings):
        missing=[]
        for key in self.PROFILE_SETTING_KEYS:
            if key not in settings: missing.append(key); continue
            self.vars[key].set(settings[key])
        self.status_text.set("Profil personnalisé appliqué." if not missing else "Profil chargé avec réglages absents : "+", ".join(missing))

    def refresh_user_profiles(self):
        profiles=ProfileManager.list_user_profiles()
        if hasattr(self,"user_profile_combo"): self.user_profile_combo.configure(values=profiles)
        selected=self.vars["user_profile"].get()
        if selected not in profiles: self.vars["user_profile"].set(profiles[0] if profiles else "")
        self.show_user_profile_description()

    def show_user_profile_description(self, _event=None):
        if not hasattr(self,"user_profile_description"): return
        name=self.vars["user_profile"].get().strip()
        if not name:
            self.user_profile_description.configure(text="Aucun profil personnel enregistré."); return
        description=ProfileManager.profile_description(name)
        self.user_profile_description.configure(text=description or "Profil personnel sans description.")

    def save_user_profile_as(self):
        name=simpledialog.askstring("Nouveau profil","Nom du profil personnalisé :",parent=self)
        if not name: return
        description=simpledialog.askstring("Description","Description du profil :",parent=self) or ""
        try:
            path=ProfileManager.save_user_profile(name,description,self.collect_profile_settings())
            self.refresh_user_profiles(); self.vars["user_profile"].set(name); self.show_user_profile_description()
            self.status_text.set(f"Profil enregistré : {path}")
        except Exception as error:
            messagebox.showerror("Enregistrement du profil",str(error))

    def update_user_profile(self):
        name=self.vars["user_profile"].get().strip()
        if not name:
            messagebox.showwarning("Profil","Sélectionnez d'abord un profil personnel."); return
        try:
            path=ProfileManager.save_user_profile(name,ProfileManager.profile_description(name),self.collect_profile_settings())
            self.status_text.set(f"Profil mis à jour : {path}")
        except Exception as error:
            messagebox.showerror("Mise à jour du profil",str(error))

    def load_user_profile(self):
        name=self.vars["user_profile"].get().strip()
        if not name:
            messagebox.showwarning("Profil","Aucun profil personnel sélectionné."); return
        try:
            self.apply_profile_settings(ProfileManager.load_user_profile(name))
            self.show_user_profile_description(); self.status_text.set(f"Profil chargé : {name}")
        except Exception as error:
            messagebox.showerror("Chargement du profil",str(error))

    def delete_user_profile(self):
        name=self.vars["user_profile"].get().strip()
        if not name: return
        if not messagebox.askyesno("Supprimer le profil",f"Supprimer définitivement le profil « {name} » ?"): return
        try:
            ProfileManager.delete_user_profile(name); self.refresh_user_profiles(); self.status_text.set(f"Profil supprimé : {name}")
        except Exception as error:
            messagebox.showerror("Suppression du profil",str(error))

    def apply_selected_profiles(self):
        try:
            settings = ProfileManager.build(
                self.vars["profile_terrain"].get(),
                self.vars["profile_style"].get(),
                self.vars["profile_quality"].get(),
            )

            mapping = {
                "camera_mode": "camera_mode",
                "orientation": "orientation",
                "distance_min": "distance_min",
                "distance_max": "distance_max",
                "distance_scale": "distance_scale",
                "height_min": "height_min",
                "height_max": "height_max",
                "height_scale": "height_scale",
                "lateral_min": "lateral_min",
                "lateral_max": "lateral_max",
                "lateral_scale": "lateral_scale",
                "look_ahead": "look_ahead",
                "smoothing": "smoothing",
                "terrain_margin": "terrain_margin",
                "terrain_max_cells": "terrain_max_cells",
                "terrain_zoom": "terrain_zoom",
                "fps": "fps",
                "resolution": "resolution",
            }

            for setting_name, variable_name in mapping.items():
                self.vars[variable_name].set(settings[setting_name])

            self.status_text.set(
                "Profils appliqués : "
                f"{self.vars['profile_terrain'].get()} / "
                f"{self.vars['profile_style'].get()} / "
                f"{self.vars['profile_quality'].get()}"
            )
        except Exception as error:
            messagebox.showerror("Profils", str(error))

    @staticmethod
    def project_path_for_gpx(gpx_path):
        return Path("projects") / f"{Path(gpx_path).stem}.yaml"

    def template_project_file(self):
        for candidate in (
            Path("projects/project_v5.yaml"),
            Path("projects/project_template.yaml"),
        ):
            if candidate.exists():
                return candidate

        raise FileNotFoundError(
            "Aucun projet modèle trouvé dans projects."
        )

    def open_or_create_project_for_gpx(self, gpx_path):
        gpx_path = Path(gpx_path)

        if not gpx_path.exists():
            raise FileNotFoundError(f"GPX introuvable : {gpx_path}")

        if gpx_path.suffix.lower() != ".gpx":
            raise ValueError("Le fichier doit être au format .gpx.")

        project_path = self.project_path_for_gpx(gpx_path)

        if project_path.exists():
            project = ProjectLoaderV5(project_path).load()
            project.gpx.file = gpx_path
            project.source_file = project_path

            self.project = project
            self.project_file.set(str(project_path))
            self._fill_form()
            self.status_text.set(
                f"Projet existant chargé : {project_path}"
            )
            self.after(
                100,
                self.propose_profile_for_current_project,
            )
            return

        template = ProjectLoaderV5(
            self.template_project_file()
        ).load()

        template.title = gpx_path.stem.replace("_", " ")
        template.gpx.file = gpx_path
        template.source_file = project_path

        self.project = template
        self.project_file.set(str(project_path))

        ProjectLoaderV5.save(self.project, project_path)
        self._fill_form()

        self.status_text.set(
            f"Nouveau projet créé automatiquement : {project_path}"
        )
        self.after(
            100,
            self.propose_profile_for_current_project,
        )

    def create_project_from_gpx(self):
        self.choose_gpx()

    def choose_project(self):
        filename = filedialog.askopenfilename(
            title="Ouvrir exceptionnellement un projet YAML",
            filetypes=[("Projet YAML", "*.yaml *.yml")],
        )

        if filename:
            self.load_project(Path(filename))

    def choose_gpx(self):
        filename = filedialog.askopenfilename(
            title="Choisir le GPX du projet",
            initialdir="gpx",
            filetypes=[("Fichier GPX", "*.gpx")],
        )

        if not filename:
            return

        try:
            self.open_or_create_project_for_gpx(Path(filename))
        except Exception as error:
            messagebox.showerror("Ouverture du GPX", str(error))

    def _profile_details_text(self, match):
        lines = [
            f"Profil : {match.label}",
            f"Score : {match.score:.1f} %",
            f"Confiance : {match.confidence:.1f} %",
            "",
            "Pourquoi :",
        ]

        if match.reasons:
            lines.extend(
                f"  + {reason}"
                for reason in match.reasons
            )
        else:
            lines.append("  Aucun critère positif disponible.")

        if match.warnings:
            lines.extend(
                ["", "Écarts :"]
                + [
                    f"  - {warning}"
                    for warning in match.warnings
                ]
            )

        lines.extend(["", "Réglages proposés :"])

        for key, value in match.proposed_settings.items():
            display = (
                f"{value:.2f}"
                if isinstance(value, float)
                else str(value)
            )
            lines.append(f"  {key} = {display}")

        return "\n".join(lines)

    def apply_profile_match(self, match):
        if self.project is None:
            return

        project = self.project
        settings = match.proposed_settings

        mapping = {
            "camera.distance.minimum": (
                project.camera.distance,
                "minimum",
            ),
            "camera.distance.maximum": (
                project.camera.distance,
                "maximum",
            ),
            "camera.height.minimum": (
                project.camera.height,
                "minimum",
            ),
            "camera.height.maximum": (
                project.camera.height,
                "maximum",
            ),
            "camera.look_ahead": (
                project.camera,
                "look_ahead",
            ),
            "camera.smoothing": (
                project.camera,
                "smoothing",
            ),
            "terrain.max_cells": (
                project.terrain,
                "max_cells",
            ),
            "terrain.satellite_zoom": (
                project.terrain,
                "satellite_zoom",
            ),
            "timeline.travel": (
                project.timeline,
                "travel",
            ),
        }

        for key, (target, attribute) in mapping.items():
            if key in settings:
                setattr(target, attribute, settings[key])

        project.profile.selected = match.key
        project.profile.recommended = match.key
        project.profile.confidence = float(match.confidence)
        project.profile.source = "user"

        ProjectLoaderV5.save(
            project,
            project.source_file,
        )

        self._fill_form()
        self.status_text.set(
            f"Profil appliqué et enregistré : {match.label}"
        )

    def propose_profile_for_current_project(self):
        if self.project is None:
            return

        try:
            metrics = analyze_gpx(self.project.gpx.file)
            matches = ProfileEngine().match(metrics)
        except Exception as error:
            messagebox.showwarning(
                "Analyse du GPX",
                f"Analyse impossible :\n{error}",
            )
            return

        if not matches:
            messagebox.showwarning(
                "Profils",
                "Aucun profil disponible.",
            )
            return

        dialog = tk.Toplevel(self)
        dialog.title("Profil conseillé pour le GPX")
        dialog.geometry("820x650")
        dialog.minsize(700, 520)
        dialog.transient(self)
        dialog.grab_set()

        recommended = matches[0]

        ttk.Label(
            dialog,
            text="Analyse automatique du GPX",
            font=("Segoe UI", 13, "bold"),
        ).pack(
            anchor="w",
            padx=14,
            pady=(14, 4),
        )

        ttk.Label(
            dialog,
            text=(
                f"Profil recommandé : {recommended.label} "
                f"— confiance {recommended.confidence:.1f} %"
            ),
        ).pack(
            anchor="w",
            padx=14,
            pady=(0, 10),
        )

        selected_key = tk.StringVar(value=recommended.key)
        matches_by_key = {
            match.key: match
            for match in matches
        }
        labels_by_key = {
            match.key: (
                f"{match.label} — {match.confidence:.1f} %"
            )
            for match in matches
        }
        keys_by_label = {
            label: key
            for key, label in labels_by_key.items()
        }

        profile_combo = ttk.Combobox(
            dialog,
            state="readonly",
            values=tuple(
                labels_by_key[match.key]
                for match in matches
            ),
            width=60,
        )
        profile_combo.set(labels_by_key[recommended.key])
        profile_combo.pack(
            fill="x",
            padx=14,
            pady=(0, 10),
        )

        text_frame = ttk.Frame(dialog)
        text_frame.pack(
            fill="both",
            expand=True,
            padx=14,
            pady=(0, 10),
        )

        details = tk.Text(
            text_frame,
            wrap="word",
            font=("Consolas", 10),
        )
        scrollbar = ttk.Scrollbar(
            text_frame,
            orient="vertical",
            command=details.yview,
        )
        details.configure(yscrollcommand=scrollbar.set)
        details.pack(
            side="left",
            fill="both",
            expand=True,
        )
        scrollbar.pack(
            side="right",
            fill="y",
        )

        def show_match(match):
            selected_key.set(match.key)
            details.configure(state="normal")
            details.delete("1.0", "end")
            details.insert(
                "1.0",
                self._profile_details_text(match),
            )
            details.configure(state="disabled")

        def on_combo_selected(_event=None):
            key = keys_by_label.get(profile_combo.get())
            if key:
                show_match(matches_by_key[key])

        profile_combo.bind(
            "<<ComboboxSelected>>",
            on_combo_selected,
        )
        show_match(recommended)

        buttons = ttk.Frame(dialog)
        buttons.pack(
            fill="x",
            padx=14,
            pady=(0, 14),
        )

        def apply_selected():
            match = matches_by_key[selected_key.get()]

            if not messagebox.askyesno(
                "Appliquer le profil",
                (
                    f"Appliquer « {match.label} » et enregistrer "
                    "les réglages dans le YAML ?"
                ),
                parent=dialog,
            ):
                return

            self.apply_profile_match(match)
            dialog.destroy()

        ttk.Button(
            buttons,
            text="Conserver les réglages actuels",
            command=dialog.destroy,
        ).pack(side="left")

        ttk.Button(
            buttons,
            text="Appliquer le profil sélectionné",
            command=apply_selected,
        ).pack(side="right")

        dialog.protocol("WM_DELETE_WINDOW", dialog.destroy)
        self.wait_window(dialog)

    @staticmethod
    def _leader_preview_float(variable, default):
        try:
            return float(variable.get())
        except (tk.TclError, ValueError, TypeError):
            return float(default)

    @staticmethod
    def _valid_hex_color(value, default="#FC4C02"):
        value = str(value).strip().upper()

        if len(value) != 7 or not value.startswith("#"):
            return default

        try:
            int(value[1:], 16)
        except ValueError:
            return default

        return value

    def _update_leader_preview(self, *_):
        if not hasattr(self, "leader_preview_canvas"):
            return

        canvas = self.leader_preview_canvas
        canvas.delete("all")

        color = self._valid_hex_color(
            self.vars["leader_color"].get()
        )

        if hasattr(self, "leader_color_swatch"):
            self.leader_color_swatch.delete("all")
            self.leader_color_swatch.create_rectangle(
                1,
                1,
                33,
                21,
                fill=color,
                outline=color,
            )

        enabled = bool(
            self.vars["leader_enabled"].get()
        )

        style = str(
            self.vars["leader_style"].get()
        ).strip().lower()

        radius_value = self._leader_preview_float(
            self.vars["leader_radius"],
            20.0,
        )
        halo_scale = self._leader_preview_float(
            self.vars["leader_halo_scale"],
            1.8,
        )
        halo_opacity = self._leader_preview_float(
            self.vars["leader_halo_opacity"],
            0.20,
        )
        trail_fraction = self._leader_preview_float(
            self.vars["leader_trail_fraction"],
            0.035,
        )
        trail_width = self._leader_preview_float(
            self.vars["leader_trail_width"],
            10.0,
        )
        trail_opacity = self._leader_preview_float(
            self.vars["leader_trail_opacity"],
            0.55,
        )

        width = max(
            1,
            int(canvas.winfo_width() or 620),
        )
        height = max(
            1,
            int(canvas.winfo_height() or 150),
        )

        center_x = int(width * 0.68)
        center_y = int(height * 0.55)

        canvas.create_text(
            14,
            14,
            anchor="nw",
            fill="#E8E8E8",
            font=("Segoe UI", 10, "bold"),
            text=(
                f"Style : {style or 'glow'}   "
                f"Couleur : {color}"
            ),
        )

        if not enabled:
            canvas.create_text(
                width // 2,
                height // 2,
                fill="#AAAAAA",
                font=("Segoe UI", 12),
                text="Leader désactivé",
            )
            return

        radius = max(
            5,
            min(
                28,
                int(round(radius_value * 0.45)),
            ),
        )

        if style in {"glow", "comet"}:
            halo_radius = max(
                radius + 2,
                min(
                    60,
                    int(round(radius * halo_scale)),
                ),
            )

            halo_stipple = (
                "gray75"
                if halo_opacity >= 0.65
                else "gray50"
                if halo_opacity >= 0.35
                else "gray25"
            )

            canvas.create_oval(
                center_x - halo_radius,
                center_y - halo_radius,
                center_x + halo_radius,
                center_y + halo_radius,
                fill=color,
                outline="",
                stipple=halo_stipple,
            )

        trail_enabled = bool(
            self.vars["leader_trail_enabled"].get()
        )

        if style == "comet" and trail_enabled:
            trail_length = max(
                35,
                min(
                    280,
                    int(round(50 + trail_fraction * 1500)),
                ),
            )
            line_width = max(
                1,
                min(
                    18,
                    int(round(trail_width * 0.55)),
                ),
            )

            trail_stipple = (
                "gray75"
                if trail_opacity >= 0.65
                else "gray50"
                if trail_opacity >= 0.35
                else "gray25"
            )

            canvas.create_line(
                center_x - trail_length,
                center_y,
                center_x - radius,
                center_y,
                fill=color,
                width=line_width,
                capstyle=tk.ROUND,
                stipple=trail_stipple,
            )

        canvas.create_oval(
            center_x - radius,
            center_y - radius,
            center_x + radius,
            center_y + radius,
            fill=color,
            outline="#FFFFFF",
            width=1,
        )

        style_description = {
            "point": "Point seul",
            "glow": "Point + halo",
            "comet": "Point + halo + traînée",
        }.get(
            style,
            "Point + halo",
        )

        canvas.create_text(
            14,
            height - 16,
            anchor="sw",
            fill="#BEBEBE",
            font=("Segoe UI", 9),
            text=style_description,
        )

    
    def choose_leader_color(self):
        selected = colorchooser.askcolor(
            color=self.vars["leader_color"].get()
        )[1]

        if selected:
            selected = selected.upper()
            self.vars["leader_color"].set(selected)

            print("Leader choisi :", selected)
            print(
                "Variable leader_color :",
                self.vars["leader_color"].get(),
            )

            self._update_leader_preview()

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

            "leader_enabled": project.leader.enabled,
            "leader_style": project.leader.style,
            "leader_color": project.leader.color,
            "leader_radius": project.leader.radius,
            "profile_marker_radius": project.leader.profile_marker_radius,
            "leader_z_offset": project.leader.z_offset,
            "leader_halo_scale": project.leader.halo_scale,
            "leader_halo_opacity": project.leader.halo_opacity,
            "leader_trail_enabled": project.leader.trail_enabled,
            "leader_trail_fraction": project.leader.trail_fraction,
            "leader_trail_width": project.leader.trail_width,
            "leader_trail_opacity": project.leader.trail_opacity,
            "leader_fade_trail_on_arrival": (
                project.leader.fade_trail_on_arrival
            ),
            "leader_trail_fade_duration": (
                project.leader.trail_fade_duration
            ),
            "leader_screen_space": project.leader.screen_space_enabled,

            "cinematic_start_centered": (
                project.cinematic.start_centered
            ),
            "cinematic_start_zoom": (
                project.cinematic.start_zoom
            ),
            "cinematic_start_transition": (
                project.cinematic.start_transition
            ),
            "cinematic_finish_zoom": (
                project.cinematic.finish_zoom
            ),

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
        values["progress_speed"] = project.timeline.speed

        for key, value in values.items():
            if key in self.vars:
                self.vars[key].set(
                    value
                )

        self._update_leader_preview()

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

        gpx_text = str(
            self.vars["gpx"].get()
        ).strip()

        if not gpx_text:
            raise ValueError(
                "Sélectionne d'abord un fichier GPX."
            )

        gpx_path = Path(
            gpx_text
        )

        if gpx_path.is_dir():
            raise ValueError(
                "Le chemin GPX désigne un dossier, "
                "pas un fichier."
            )

        if gpx_path.suffix.lower() != ".gpx":
            raise ValueError(
                "Le fichier sélectionné doit être "
                "au format .gpx."
            )

        project.gpx.file = gpx_path

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
                "leader_enabled"
            ].get()
        )

        project.leader.enabled = bool(
            self.vars[
                "leader_enabled"
            ].get()
        )

        project.leader.style = str(
            self.vars[
                "leader_style"
            ].get()
        )

        project.leader.color = str(
            self.vars[
                "leader_color"
            ].get()
        )

        project.leader.radius = float(
            self.vars[
                "leader_radius"
            ].get()
        )
        project.leader.profile_marker_radius = float(
            self.vars[
                "profile_marker_radius"
            ].get()
        )

        project.leader.z_offset = float(
            self.vars[
                "leader_z_offset"
            ].get()
        )

        project.leader.halo_scale = float(
            self.vars[
                "leader_halo_scale"
            ].get()
        )

        project.leader.halo_opacity = float(
            self.vars[
                "leader_halo_opacity"
            ].get()
        )

        project.leader.trail_enabled = bool(
            self.vars[
                "leader_trail_enabled"
            ].get()
        )

        project.leader.trail_fraction = float(
            self.vars[
                "leader_trail_fraction"
            ].get()
        )

        project.leader.trail_width = float(
            self.vars[
                "leader_trail_width"
            ].get()
        )

        project.leader.trail_opacity = float(
            self.vars[
                "leader_trail_opacity"
            ].get()
        )

        project.leader.fade_trail_on_arrival = bool(
            self.vars[
                "leader_fade_trail_on_arrival"
            ].get()
        )

        project.leader.trail_fade_duration = float(
            self.vars[
                "leader_trail_fade_duration"
            ].get()
        )

        project.leader.screen_space_enabled = bool(
            self.vars[
                "leader_screen_space"
            ].get()
        )

        project.cinematic.start_centered = bool(
            self.vars[
                "cinematic_start_centered"
            ].get()
        )
        project.cinematic.start_zoom = float(
            self.vars[
                "cinematic_start_zoom"
            ].get()
        )
        project.cinematic.start_transition = float(
            self.vars[
                "cinematic_start_transition"
            ].get()
        )
        project.cinematic.finish_zoom = float(
            self.vars[
                "cinematic_finish_zoom"
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

        project.timeline.speed = float(
            self.vars["progress_speed"].get()
        )

        for key in project.timeline.to_dict():
            if key == "speed":
                continue
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
