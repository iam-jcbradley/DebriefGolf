"""2D dispersion ellipse math (PRD §5.3 "Dispersion Cone Visualizer", §10 Phase 4).

An ellipse summarizing where a club's shots land, in the aim-line-relative
coordinates `app.services.geometry` produces: longitudinal (carry, along the
aim line) and lateral (side-to-side) axes, each sized by that axis's
standard deviation times a coverage multiplier `k`.
"""

from dataclasses import dataclass

# 1.5 standard deviations is a common "dispersion cone" convention in golf
# analytics — wide enough to read as a real pattern rather than a single
# average shot, without ballooning out to rarely-relevant outliers.
DEFAULT_K = 1.5


@dataclass(frozen=True)
class DispersionEllipse:
    center_longitudinal_yards: float
    center_lateral_yards: float
    semi_major_yards: float
    semi_minor_yards: float
    k: float


def compute_dispersion_ellipse(
    longitudinal_mean_yards: float,
    longitudinal_stdev_yards: float,
    lateral_mean_yards: float,
    lateral_stdev_yards: float,
    k: float = DEFAULT_K,
) -> DispersionEllipse:
    if longitudinal_stdev_yards < 0 or lateral_stdev_yards < 0:
        raise ValueError("standard deviations must be >= 0")
    if k <= 0:
        raise ValueError("k must be > 0")

    return DispersionEllipse(
        center_longitudinal_yards=longitudinal_mean_yards,
        center_lateral_yards=lateral_mean_yards,
        semi_major_yards=longitudinal_stdev_yards * k,
        semi_minor_yards=lateral_stdev_yards * k,
        k=k,
    )


def is_within_ellipse(
    ellipse: DispersionEllipse, longitudinal_yards: float, lateral_yards: float
) -> bool:
    """Whether a point (e.g. a pin position) falls inside the dispersion
    ellipse — the basis for a "sucker pin" strategy alert (PRD §5.3): a
    tucked pin sitting inside your typical dispersion pattern for the club
    you'd use is a high-risk aim point."""
    dx = longitudinal_yards - ellipse.center_longitudinal_yards
    dy = lateral_yards - ellipse.center_lateral_yards

    if ellipse.semi_major_yards == 0 or ellipse.semi_minor_yards == 0:
        return dx == 0 and dy == 0

    normalized = (dx / ellipse.semi_major_yards) ** 2 + (dy / ellipse.semi_minor_yards) ** 2
    return normalized <= 1.0
