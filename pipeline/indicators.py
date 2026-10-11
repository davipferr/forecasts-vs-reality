"""The four Focus indicators: what to fetch, what to score them against, how to label them."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from typing import Callable

import polars as pl

from . import actuals

# CMN inflation targets (centre, tolerance band ±pp). 2003 and 2004 use the
# revised targets (4.0 and 5.5) that replaced the original 3.25 and 3.75 in 2002–03.
IPCA_GOALS = {
    1999: (8.0, 2.0), 2000: (6.0, 2.0), 2001: (4.0, 2.0), 2002: (3.5, 2.0),
    2003: (4.0, 2.5), 2004: (5.5, 2.5), 2005: (4.5, 2.5),
    **{y: (4.5, 2.0) for y in range(2006, 2017)},
    2017: (4.5, 1.5), 2018: (4.5, 1.5), 2019: (4.25, 1.5), 2020: (4.0, 1.5),
    2021: (3.75, 1.5), 2022: (3.5, 1.5), 2023: (3.25, 1.5),
    **{y: (3.0, 1.5) for y in range(2024, 2036)},
}  # fmt: skip


@dataclass
class Indicator:
    id: str
    focus: str  # name in the Olinda "Indicador" field
    name: str
    unit: str
    actual_label: str
    naive_label: str
    notes: list[str]
    # (today) -> (actual: target, actual; known: available, value)
    sources: Callable[[date], tuple[pl.DataFrame, pl.DataFrame]]
    top5: bool = True
    goals: dict[int, tuple[float, float]] = field(default_factory=dict)

    def meta(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "unit": self.unit,
            "actualLabel": self.actual_label,
            "naiveLabel": self.naive_label,
            "notes": self.notes,
            "hasGoal": bool(self.goals),
            "hasTop5": self.top5,
        }


INDICATORS = [
    Indicator(
        id="ipca",
        focus="IPCA",
        name="IPCA inflation",
        unit="%",
        actual_label="IPCA, calendar year (compounded from monthly IBGE releases)",
        naive_label="Last published 12-month IPCA",
        notes=["The goal benchmark forecasts the CMN inflation target for every year."],
        sources=lambda today: actuals.ipca(),
        goals=IPCA_GOALS,
    ),
    Indicator(
        id="selic",
        focus="Selic",
        name="Selic rate",
        unit="%",
        actual_label="Copom's Selic target on 31 December",
        naive_label="The Selic target on the survey date",
        notes=[],
        sources=actuals.selic,
    ),
    Indicator(
        id="gdp",
        focus="PIB Total",
        name="GDP growth",
        unit="%",
        actual_label="Real GDP growth (IBGE, current revised figures)",
        naive_label="Last published annual GDP growth",
        notes=[
            "Scored against today's revised GDP figures, not the first release the market saw.",
            "The Top 5 ranking for GDP only exists since 2023, too short to compare.",
        ],
        sources=lambda today: actuals.gdp(),
        top5=False,
    ),
    Indicator(
        id="fx",
        focus="Câmbio",
        name="Exchange rate",
        unit="R$/US$",
        actual_label="December average PTAX rate (R$ per US$)",
        naive_label="Previous day's PTAX rate",
        notes=[
            "Scored against the December average PTAX: where it differs from the 31 December rate, "
            "the final forecasts sit on the average.",
        ],
        sources=actuals.fx,
    ),
]

BY_ID = {ind.id: ind for ind in INDICATORS}


def goals_frame(ind: Indicator) -> pl.DataFrame:
    return pl.DataFrame(
        {
            "target": list(ind.goals),
            "goal": [g[0] for g in ind.goals.values()],
            "goal_tolerance": [g[1] for g in ind.goals.values()],
        },
        schema={"target": pl.Int32, "goal": pl.Float64, "goal_tolerance": pl.Float64},
    )
