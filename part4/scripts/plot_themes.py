from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd
from matplotlib.ticker import PercentFormatter

PART4 = Path(__file__).resolve().parent.parent
YEARLY = PART4 / "data" / "final" / "theme_by_year.csv"
VISUALIZATIONS = PART4 / "visualizations"

ABOUT_COLOR, PROXY_COLOR = "#e8590c", "#7b4bc4"


def label(theme):
    """Turn a theme column name into a readable name."""
    return "Diversity and inclusion" if theme == "diversity_inclusion" else theme.capitalize()


def draw(ax, g, theme, small=False):
    """Draw the About page and proxy lines for one theme on an axis."""
    ax.plot(g.year, g.about_page_pct, marker="o", color=ABOUT_COLOR, linewidth=2.2, label="About Us pages")
    ax.plot(g.year, g.proxy_pct, marker="o", color=PROXY_COLOR, linewidth=2.2, label="Proxy statements")
    ax.set_ylim(0, 100 if small else 108)
    ax.set_yticks(range(0, 101, 20))
    ax.yaxis.set_major_formatter(PercentFormatter())
    ax.grid(axis="y", linestyle="--", alpha=0.25)
    ax.spines[["top", "right"]].set_visible(False)
    ax.set_title(label(theme) if small else f"{label(theme)} over time", fontsize=12 if small else 15, loc="left")


def crossings(g):
    """Return the points where the two lines meet, interpolating between years."""
    years, about, proxy = g.year.values, g.about_page_pct.values, g.proxy_pct.values
    diff = proxy - about
    points = [(years[i], about[i]) for i in range(len(diff)) if diff[i] == 0]
    for i in range(len(diff) - 1):
        if diff[i] * diff[i + 1] < 0:
            t = diff[i] / (diff[i] - diff[i + 1])
            points.append((years[i] + t, about[i] + t * (about[i + 1] - about[i])))
    return sorted(points)


def annotate(ax, g):
    """Label every crossing point, or each line's highest and lowest point if the lines never cross."""
    points = crossings(g)
    if points:
        for x, y in points:
            ax.plot(x, y, marker="X", color="black", markersize=9, zorder=5)
            ax.annotate(f"{y:.0f}%", (x, y), textcoords="offset points", xytext=(0, 9), ha="center", fontsize=9)
        return
    for column, color in [("about_page_pct", ABOUT_COLOR), ("proxy_pct", PROXY_COLOR)]:
        for row, offset in [(g.loc[g[column].idxmax()], 9), (g.loc[g[column].idxmin()], -15)]:
            ax.annotate(f"{row[column]:.0f}%", (row.year, row[column]), textcoords="offset points",
                        xytext=(0, offset), ha="center", fontsize=9, color=color)


def plot_theme(g, theme):
    """Save one chart for a single theme."""
    fig, ax = plt.subplots(figsize=(9, 5.2))
    draw(ax, g, theme)
    annotate(ax, g)
    ax.set_xlabel("Year")
    ax.set_ylabel(f"% of companies discussing {label(theme).lower()}")
    ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.15), ncol=2, frameon=False)
    fig.tight_layout()
    fig.savefig(VISUALIZATIONS / f"{theme}.png", dpi=150)
    plt.close(fig)


def plot_overview(yearly):
    """Save one figure with a small chart for every theme."""
    fig, axes = plt.subplots(2, 5, figsize=(18, 7.5), sharex=True, sharey=True)
    for ax, (theme, g) in zip(axes.flat, yearly.groupby("theme", sort=False)):
        draw(ax, g, theme, small=True)
    handles, labels = axes[0, 0].get_legend_handles_labels()
    fig.legend(handles, labels, loc="lower center", ncol=2, frameon=False, fontsize=12)
    fig.supxlabel("Year", y=0.07)
    fig.supylabel("% of companies discussing the theme", x=0.005)
    fig.suptitle("Share of companies discussing each theme: About Us pages vs proxy statements", fontsize=16)
    fig.tight_layout(rect=(0.015, 0.06, 1, 0.95))
    fig.savefig(VISUALIZATIONS / "all_themes.png", dpi=150)
    plt.close(fig)


def main():
    """Draw a chart for each theme and an overview of all themes."""
    yearly = pd.read_csv(YEARLY)
    VISUALIZATIONS.mkdir(exist_ok=True)
    for theme, g in yearly.groupby("theme", sort=False):
        plot_theme(g, theme)
    plot_overview(yearly)
    print(f"Saved {yearly.theme.nunique() + 1} charts to visualizations/")


main()
