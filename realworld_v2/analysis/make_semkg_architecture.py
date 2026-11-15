"""Render the compact SemKG method overview for the paper."""

from pathlib import Path

import matplotlib.pyplot as plt
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch


OUT = Path(__file__).resolve().parents[2] / "semkg_agents/figures/semkg_method_architecture.png"


COLORS = {
    "ink": "#243447",
    "muted": "#5B6B7A",
    "line": "#B8C5D1",
    "input": "#EAF2F6",
    "graph": "#DCEEEA",
    "control": "#E8E4F4",
    "agent": "#F8E9D5",
    "verify": "#F5E0E2",
    "white": "#FFFFFF",
}


def box(ax, x, y, w, h, title, subtitle, face, title_size=9.7):
    patch = FancyBboxPatch(
        (x, y), w, h,
        boxstyle="round,pad=0.018,rounding_size=0.035",
        linewidth=1.1,
        edgecolor=COLORS["line"],
        facecolor=face,
        zorder=2,
    )
    ax.add_patch(patch)
    ax.text(x + w / 2, y + h * 0.66, title, ha="center", va="center",
            fontsize=title_size, fontweight="bold", color=COLORS["ink"], zorder=3)
    ax.text(x + w / 2, y + h * 0.28, subtitle, ha="center", va="center",
            fontsize=7.6, color=COLORS["muted"], linespacing=1.15, zorder=3)


def arrow(ax, start, end, label=None, dashed=False, color=None, label_y=None):
    color = color or COLORS["ink"]
    style = (0, (3.0, 2.5)) if dashed else "-"
    a = FancyArrowPatch(
        start, end,
        arrowstyle="-|>",
        mutation_scale=11,
        linewidth=1.7 if not dashed else 1.25,
        linestyle=style,
        color=color,
        connectionstyle="arc3,rad=0",
        zorder=1,
    )
    ax.add_patch(a)
    if label:
        x = (start[0] + end[0]) / 2
        y = label_y if label_y is not None else (start[1] + end[1]) / 2 + 0.075
        ax.text(x, y, label, ha="center", va="bottom", fontsize=7.6,
                color=COLORS["muted"], zorder=4,
                bbox={"facecolor": COLORS["white"], "edgecolor": "none", "pad": 1.3})


def main():
    fig, ax = plt.subplots(figsize=(5.0, 2.6), dpi=300)
    fig.patch.set_facecolor("white")
    ax.set_xlim(0, 10.4)
    ax.set_ylim(0, 4.2)
    ax.axis("off")

    ax.text(0.12, 4.02, "SemKG: coordination under contract evolution", fontsize=10.0,
            fontweight="bold", color=COLORS["ink"], ha="left", va="center")
    xs = [0.15, 2.70, 5.25, 7.80]
    w, h = 2.10, 1.02
    box(ax, xs[0], 2.25, w, h, "Semantic\nevidence", "reads + artifacts", COLORS["input"])
    box(ax, xs[1], 2.25, w, h, "Versioned\nSemKG", "facts + versions", COLORS["graph"])
    box(ax, xs[2], 2.25, w, h, "Impact\ncontroller", "typed reachability", COLORS["control"])
    box(ax, xs[3], 2.25, w, h, "Selective\nscheduler", "requeue set $I$", COLORS["control"])
    for left, right in zip(xs, xs[1:]):
        arrow(ax, (left + w, 2.76), (right, 2.76))

    box(ax, xs[0], .40, w, h, "Plan +\ncontract", "fingerprint", COLORS["agent"])
    box(ax, xs[1], .40, w, h, "Coding\nagents", "patch + $A_v$", COLORS["agent"])
    box(ax, xs[2], .40, w, h, "Verification", "tests + invariants", COLORS["verify"])
    box(ax, xs[3], .40, w, h, "Atomic\ncommit gate", "version check", COLORS["graph"])
    for left, right in zip(xs, xs[1:]):
        arrow(ax, (left + w, .91), (right, .91))

    # Orthogonal routes avoid the crossing diagonal labels of the old figure.
    ax.plot([8.85, 8.85, 1.20], [2.25, 1.82, 1.82], color=COLORS["ink"], linewidth=1.7)
    arrow(ax, (1.20, 1.82), (1.20, 1.42))
    ax.text(4.95, 1.86, "dispatch / re-dispatch", ha="center", va="bottom", fontsize=8.0, color=COLORS["ink"])
    arrow(ax, (9.42, 2.25), (9.42, 1.95), color=COLORS["muted"])
    ax.text(9.00, 1.65, "others continue", ha="center", va="center", fontsize=7.6, color=COLORS["muted"])

    ax.plot([9.90, 10.20, 10.20, 3.75], [.91, .91, 3.62, 3.62],
            color=COLORS["muted"], linewidth=1.25, linestyle=(0, (3, 2.5)))
    arrow(ax, (3.75, 3.62), (3.75, 3.27), dashed=True, color=COLORS["muted"])
    ax.text(6.90, 3.65, "commit evidence", fontsize=8.0, color=COLORS["muted"], ha="center", va="bottom")
    ax.text(.15, .08, "Solid: control flow     Dashed: evidence feedback", fontsize=7.8, color=COLORS["muted"], va="center")

    fig.tight_layout(pad=0.25)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(OUT, dpi=300, bbox_inches="tight", facecolor="white")
    fig.savefig(OUT.with_suffix(".pdf"), bbox_inches="tight", facecolor="white")
    plt.close(fig)


if __name__ == "__main__":
    main()
