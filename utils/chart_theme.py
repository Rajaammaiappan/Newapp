"""Shared Plotly styling so every chart matches the app theme."""
PRIMARY = "#6c5ce7"
SECONDARY = "#00cec9"
SUCCESS = "#00b894"
DANGER = "#e17055"

LAYOUT = dict(
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(0,0,0,0)",
    font=dict(family="Inter, sans-serif", color="#9aa4b2", size=12),
    margin=dict(l=10, r=10, t=30, b=10),
    xaxis=dict(gridcolor="rgba(255,255,255,0.06)", zeroline=False),
    yaxis=dict(gridcolor="rgba(255,255,255,0.06)", zeroline=False),
    hoverlabel=dict(bgcolor="#1a1f2b", font_color="#f5f6fa"),
    legend=dict(orientation="h", y=1.1),
)


def style(fig):
    fig.update_layout(**LAYOUT)
    return fig
