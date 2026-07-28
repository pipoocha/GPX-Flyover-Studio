from __future__ import annotations

import math
from collections.abc import Iterable

from studio.profiles.catalog import PROFILE_CATALOG
from studio.profiles.models import ProfileDefinition, ProfileMatch


class ProfileEngine:
    def __init__(
        self,
        catalog: Iterable[ProfileDefinition] = PROFILE_CATALOG,
    ):
        self.catalog = tuple(catalog)

    @staticmethod
    def _metric_score(
        value: float,
        rule: dict,
    ) -> tuple[float, str, bool]:
        minimum = rule.get("min")
        maximum = rule.get("max")
        weight = float(rule.get("weight", 1.0))

        if minimum is not None and value < float(minimum):
            distance = float(minimum) - value
            scale = max(abs(float(minimum)), 10.0)
            score = max(0.0, 1.0 - distance / scale)
            explanation = (
                f"{value:.1f} inférieur au seuil conseillé "
                f"{float(minimum):.1f}"
            )
            return score * weight, explanation, False

        if maximum is not None and value > float(maximum):
            distance = value - float(maximum)
            scale = max(abs(float(maximum)), 10.0)
            score = max(0.0, 1.0 - distance / scale)
            explanation = (
                f"{value:.1f} supérieur au seuil conseillé "
                f"{float(maximum):.1f}"
            )
            return score * weight, explanation, False

        if minimum is not None and maximum is not None:
            center = (float(minimum) + float(maximum)) / 2.0
            half_range = max(
                1.0,
                (float(maximum) - float(minimum)) / 2.0,
            )
            normalized = abs(value - center) / half_range
            score = 1.0 - min(0.25, normalized * 0.15)
        else:
            score = 1.0

        if minimum is not None and maximum is not None:
            explanation = (
                f"{value:.1f} dans la plage "
                f"{float(minimum):.1f}–{float(maximum):.1f}"
            )
        elif minimum is not None:
            explanation = (
                f"{value:.1f} au-dessus du minimum "
                f"{float(minimum):.1f}"
            )
        else:
            explanation = (
                f"{value:.1f} sous le maximum "
                f"{float(maximum):.1f}"
            )

        return score * weight, explanation, True

    @staticmethod
    def _proposed_settings(
        profile: ProfileDefinition,
        metrics: dict,
    ) -> dict:
        settings = dict(profile.base_settings)

        distance_km = float(
            metrics.get("distance_total_km", 0.0)
        )
        terrain_width = float(
            metrics.get("recommended_terrain_width_km", 0.0)
        )
        terrain_height = float(
            metrics.get("recommended_terrain_height_km", 0.0)
        )
        maximum_span = float(
            metrics.get("footprint_max_span_km", 0.0)
        )
        relief_index = float(
            metrics.get("relief_index_percent", 0.0) or 0.0
        )

        seconds_per_km = float(
            settings.pop(
                "timeline.travel_seconds_per_km",
                1.25,
            )
        )

        settings["timeline.travel"] = max(
            12.0,
            min(120.0, distance_km * seconds_per_km),
        )

        settings["terrain.recommended_width_km"] = terrain_width
        settings["terrain.recommended_height_km"] = terrain_height

        distance_factor = max(
            0.85,
            min(1.35, maximum_span / 8.0),
        )
        relief_factor = 0.90 + min(0.35, relief_index / 300.0)

        for key in (
            "camera.distance.minimum",
            "camera.distance.maximum",
        ):
            settings[key] = int(
                round(
                    float(settings[key])
                    * distance_factor
                )
            )

        for key in (
            "camera.height.minimum",
            "camera.height.maximum",
        ):
            settings[key] = int(
                round(
                    float(settings[key])
                    * relief_factor
                )
            )

        return settings

    def match(
        self,
        metrics: dict,
    ) -> list[ProfileMatch]:
        matches = []

        for profile in self.catalog:
            weighted_score = 0.0
            maximum_score = 0.0
            reasons = []
            warnings = []
            matched_rules = 0

            for metric_name, rule in profile.rules.items():
                value = metrics.get(metric_name)

                if value is None:
                    warnings.append(
                        f"Mesure absente : {metric_name}"
                    )
                    continue

                weight = float(rule.get("weight", 1.0))
                maximum_score += weight

                score, explanation, matched = (
                    self._metric_score(
                        float(value),
                        rule,
                    )
                )

                weighted_score += score

                if matched:
                    matched_rules += 1
                    reasons.append(
                        f"{metric_name} : {explanation}"
                    )
                else:
                    warnings.append(
                        f"{metric_name} : {explanation}"
                    )

            score_percent = (
                weighted_score
                / max(maximum_score, 1e-9)
                * 100.0
            )

            rule_coverage = (
                matched_rules
                / max(1, len(profile.rules))
            )

            geometry_confidence = float(
                metrics.get(
                    "geometry_confidence_percent",
                    100.0,
                )
            ) / 100.0

            relief_confidence = float(
                metrics.get(
                    "relief_confidence_percent",
                    100.0,
                )
            ) / 100.0

            confidence = (
                score_percent
                * (
                    0.45
                    + 0.25 * rule_coverage
                    + 0.15 * geometry_confidence
                    + 0.15 * relief_confidence
                )
            )

            confidence = max(
                0.0,
                min(100.0, confidence),
            )

            matches.append(
                ProfileMatch(
                    key=profile.key,
                    label=profile.label,
                    score=score_percent,
                    confidence=confidence,
                    reasons=reasons,
                    warnings=warnings,
                    proposed_settings=self._proposed_settings(
                        profile,
                        metrics,
                    ),
                )
            )

        return sorted(
            matches,
            key=lambda match: (
                match.confidence,
                match.score,
            ),
            reverse=True,
        )
