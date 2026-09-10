"""LinkedIn restyles of experiment 08 findings. Spends no API calls.

All rates come from results/llm/llm_rates.csv (neutral arm, pooled cells).
Counts are inlined as k/n so every bar carries its own Wilson interval and
the 1/6 chance line is drawn on every panel.
"""

from __future__ import annotations

from math import sqrt
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

HERE = Path(__file__).resolve().parent
NAVY = "#1f4e79"
INK = "#222222"
MUTED = "#555555"
BAR = "#c45c4a"
GREY = "#8aa0b5"
CHANCE = "#777777"

N_TOOLS = 6
CHANCE_RATE = 1 / N_TOOLS

plt.rcParams.update(
    {
        "font.family": "sans-serif",
        "axes.edgecolor": "#cccccc",
        "axes.linewidth": 0.8,
        "axes.titlesize": 13,
        "axes.labelsize": 11,
        "xtick.labelsize": 10,
        "ytick.labelsize": 10,
    }
)


def wilson(k: int, n: int, z: float = 1.96) -> tuple[float, float]:
    """95% Wilson score interval for a binomial proportion."""
    if n == 0:
        return (0.0, 0.0)
    p = k / n
    denom = 1 + z * z / n
    centre = (p + z * z / (2 * n)) / denom
    half = z * sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / denom
    return (max(0.0, centre - half), min(1.0, centre + half))


def _err(counts: list[tuple[int, int]]) -> list[list[float]]:
    """Asymmetric yerr (in percentage points) from Wilson intervals."""
    lo_err, hi_err = [], []
    for k, n in counts:
        rate = k / n if n else 0.0
        lo, hi = wilson(k, n)
        lo_err.append((rate - lo) * 100)
        hi_err.append((hi - rate) * 100)
    return [lo_err, hi_err]


def _chance_line(ax: plt.Axes, side: str = "right") -> None:
    ax.axhline(
        CHANCE_RATE * 100,
        color=CHANCE,
        linestyle="--",
        linewidth=1.1,
        zorder=1,
    )
    x, ha = (0.995, "right") if side == "right" else (0.005, "left")
    ax.annotate(
        f"azar con {N_TOOLS} tools ({CHANCE_RATE * 100:.1f}%)",
        xy=(x, CHANCE_RATE * 100),
        xycoords=("axes fraction", "data"),
        ha=ha,
        va="bottom",
        fontsize=8.5,
        color=CHANCE,
        xytext=(0, 3),
        textcoords="offset points",
    )


def _label_bars(ax: plt.Axes, bars, counts: list[tuple[int, int]], err) -> None:
    for bar, (k, n), hi in zip(bars, counts, err[1]):
        rate = k / n if n else 0.0
        ax.annotate(
            f"{rate * 100:.0f}%",
            (bar.get_x() + bar.get_width() / 2, bar.get_height() + hi),
            ha="center",
            va="bottom",
            fontsize=10.5,
            color=INK,
            xytext=(0, 4),
            textcoords="offset points",
        )


def _style(ax: plt.Axes, title: str) -> None:
    ax.set_ylim(0, 100)
    ax.set_ylabel("% de veces que eligió la tool envenenada")
    ax.set_title(title)
    ax.grid(True, axis="y", alpha=0.3)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.set_axisbelow(True)


def _finish(fig: plt.Figure, path: Path, footer: str) -> None:
    fig.tight_layout(rect=(0.0, 0.08, 1.0, 1.0))
    fig.text(0.5, 0.02, footer, ha="center", fontsize=8.5, color=MUTED)
    fig.savefig(path, dpi=160, facecolor="white")
    plt.close(fig)
    print(f"wrote {path.name}")


# --------------------------------------------------------------------------
# Figure 1 — form vs meaning, one model, matched N=60 per bar (axis A)
# --------------------------------------------------------------------------
def variants_llama() -> None:
    # Tick labels say the condition, not the internal cell name: `trusted`
    # omits the poisoned tool entirely, so its 0% is a structural zero, not a
    # measured refusal. Cell ids stay in the footer for traceability.
    labels = [
        "sin tool\nenvenenada",
        "descripción\nirrelevante",
        "solo\nsignificado",
        "significado\n+ forma",
    ]
    counts = [(0, 60), (0, 60), (6, 60), (46, 60)]
    err = _err(counts)

    fig, ax = plt.subplots(figsize=(8.2, 5.0))
    bars = ax.bar(
        labels,
        [k / n * 100 for k, n in counts],
        color=BAR,
        edgecolor=INK,
        linewidth=0.8,
        zorder=2,
    )
    ax.errorbar(
        range(len(counts)),
        [k / n * 100 for k, n in counts],
        yerr=err,
        fmt="none",
        ecolor=INK,
        elinewidth=1.1,
        capsize=4,
        zorder=3,
    )
    _chance_line(ax, side="left")
    _label_bars(ax, bars, counts, err)
    _style(ax, "Llama 3.1 8B · forma vs significado")
    _finish(
        fig,
        HERE / "linkedin-llama-variants.png",
        "Llama 3.1 8B Instruct · N=60 por barra · IC95 Wilson · eje A (trusted / bland / semantic / template)",
    )


# --------------------------------------------------------------------------
# Figure 2 — same payload, three models, pooled N=180
# --------------------------------------------------------------------------
def models_split() -> None:
    # Pool A-template / B-L3 / C-1.00 (same payload, three independent draws).
    labels = ["Llama 3.1 8B", "Haiku 4.5", "Sonnet 5"]
    counts = [(122, 180), (96, 180), (0, 180)]
    colors = [BAR, NAVY, GREY]
    err = _err(counts)

    fig, ax = plt.subplots(figsize=(8.2, 5.0))
    bars = ax.bar(
        labels,
        [k / n * 100 for k, n in counts],
        color=colors,
        edgecolor=INK,
        linewidth=0.8,
        zorder=2,
    )
    ax.errorbar(
        range(len(counts)),
        [k / n * 100 for k, n in counts],
        yerr=err,
        fmt="none",
        ecolor=INK,
        elinewidth=1.1,
        capsize=4,
        zorder=3,
    )
    _chance_line(ax)
    _label_bars(ax, bars, counts, err)
    _style(ax, "Misma receta, tres modelos")
    _finish(
        fig,
        HERE / "linkedin-tres-modelos.png",
        "Mismo payload · 3 sorteos agrupados (A-template, B-L3, C-1.00) · N=180 por modelo · IC95 Wilson",
    )


if __name__ == "__main__":
    variants_llama()
    models_split()
