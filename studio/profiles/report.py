from __future__ import annotations

from studio.profiles.models import ProfileMatch


def print_profile_report(
    matches: list[ProfileMatch],
    limit: int = 5,
) -> None:
    print()
    print("=" * 68)
    print("PROFILS PROPOSÉS — PROFILE ENGINE V5.7 P1")
    print("=" * 68)

    for rank, match in enumerate(
        matches[: max(1, int(limit))],
        start=1,
    ):
        marker = "RECOMMANDÉ" if rank == 1 else f"CHOIX {rank}"

        print()
        print(
            f"{marker} — {match.label}"
        )
        print(
            f"Score : {match.score:.1f} % | "
            f"Confiance : {match.confidence:.1f} %"
        )

        if match.reasons:
            print("Pourquoi :")
            for reason in match.reasons:
                print("  +", reason)

        if match.warnings:
            print("Écarts :")
            for warning in match.warnings:
                print("  -", warning)

        print("Réglages proposés :")
        for key, value in match.proposed_settings.items():
            if isinstance(value, float):
                display = f"{value:.2f}"
            else:
                display = str(value)

            print(f"  {key:<38} {display}")

    print()
    print(
        "Aucun réglage n'est appliqué et le YAML n'est pas modifié."
    )
    print("=" * 68)
