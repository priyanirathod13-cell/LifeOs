import json
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# LifeOS Design System Palette
THEME = {
    'bg': '#1B1F2A',
    'paper_bg': '#1B1F2A',
    'text': '#F3F4F6',
    'muted': '#9CA3AF',
    'grid': '#2A2F3A',
    'indigo': '#818CF8',
    'purple': '#A78BFA',
    'emerald': '#34D399',
    'amber': '#FBBF24',
    'rose': '#F87171',
    'sky': '#38BDF8',
    'pink': '#F472B6',
}

FONT_FAMILY = "Inter, -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif"


def get_base_layout(title='', height=320):
    """Returns standard base layout styling adhering to LifeOS dark theme."""
    return dict(
        title=dict(
            text=title,
            font=dict(family=FONT_FAMILY, size=15, color=THEME['text']),
            x=0.02,
            y=0.96,
        ),
        paper_bgcolor=THEME['paper_bg'],
        plot_bgcolor=THEME['bg'],
        font=dict(family=FONT_FAMILY, color=THEME['text'], size=12),
        margin=dict(l=45, r=30, t=45, b=40),
        height=height,
        autosize=True,
        hovermode='x unified',
        legend=dict(
            orientation='h',
            yanchor='bottom',
            y=1.02,
            xanchor='right',
            x=1,
            font=dict(size=11, color=THEME['muted'])
        ),
    )


def figure_to_html(fig, empty_msg='No data recorded for this period'):
    """
    Renders Plotly figure to responsive standalone HTML snippet.
    Returns graceful fallback if figure has no data.
    """
    if not fig or not getattr(fig, 'data', None):
        return f"""
        <div class="empty-state" style="padding: 2.5rem 1rem; text-align: center; background: {THEME['bg']}; border-radius: 8px; border: 1px dashed {THEME['grid']};">
            <p style="color: {THEME['muted']}; font-size: 0.9rem; margin: 0;">{empty_msg}</p>
        </div>
        """
    return fig.to_html(
        full_html=False,
        include_plotlyjs=False,
        config={'responsive': True, 'displayModeBar': False}
    )


def render_productivity_trend_chart(dates, completed_counts, minutes_spent):
    """
    Dual-axis line/bar chart displaying tasks completed (bars) and minutes tracked (line).
    """
    if not dates or not any(completed_counts or minutes_spent):
        return figure_to_html(None, 'No task activity recorded in this period')

    fig = make_subplots(specs=[[{"secondary_y": True}]])

    # Minutes Tracked as Bar
    hours_spent = [round(m / 60.0, 1) for m in minutes_spent]
    fig.add_trace(
        go.Bar(
            x=dates,
            y=hours_spent,
            name='Tracked Hours',
            marker_color=THEME['indigo'],
            opacity=0.75,
            hovertemplate='%{y:.1f} hrs<extra></extra>',
        ),
        secondary_y=False,
    )

    # Tasks Completed as Line
    fig.add_trace(
        go.Scatter(
            x=dates,
            y=completed_counts,
            name='Tasks Completed',
            mode='lines+markers',
            line=dict(color=THEME['emerald'], width=2.5),
            marker=dict(size=6, color=THEME['emerald']),
            hovertemplate='%{y} tasks<extra></extra>',
        ),
        secondary_y=True,
    )

    layout = get_base_layout('Daily Productivity & Hours Tracked', height=300)
    fig.update_layout(layout)
    fig.update_xaxes(
        gridcolor=THEME['grid'],
        zerolinecolor=THEME['grid'],
        tickfont=dict(color=THEME['muted']),
    )
    fig.update_yaxes(
        title_text='Hours',
        title_font=dict(size=11, color=THEME['muted']),
        gridcolor=THEME['grid'],
        tickfont=dict(color=THEME['muted']),
        secondary_y=False,
    )
    fig.update_yaxes(
        title_text='Tasks',
        title_font=dict(size=11, color=THEME['muted']),
        gridcolor='rgba(0,0,0,0)',
        tickfont=dict(color=THEME['muted']),
        secondary_y=True,
    )
    return figure_to_html(fig)


def render_study_hours_bar_chart(dates, hours_list):
    """
    Daily study hours bar chart with soft indigo bars.
    """
    if not dates or not any(hours_list):
        return figure_to_html(None, 'No study sessions recorded in this period')

    fig = go.Figure(data=[
        go.Bar(
            x=dates,
            y=hours_list,
            name='Study Hours',
            marker_color=THEME['purple'],
            hovertemplate='%{x}: <b>%{y:.1f}h</b><extra></extra>',
        )
    ])
    layout = get_base_layout('Daily Study Hours', height=280)
    fig.update_layout(layout)
    fig.update_xaxes(gridcolor=THEME['grid'], tickfont=dict(color=THEME['muted']))
    fig.update_yaxes(title_text='Hours', gridcolor=THEME['grid'], tickfont=dict(color=THEME['muted']))
    return figure_to_html(fig)


def render_subject_comparison_chart(subject_names, hours_list, colors=None):
    """
    Horizontal bar chart showing study duration per subject.
    """
    if not subject_names or not any(hours_list):
        return figure_to_html(None, 'No subject study sessions recorded')

    default_palette = [THEME['indigo'], THEME['purple'], THEME['sky'], THEME['emerald'], THEME['amber'], THEME['rose']]
    bar_colors = colors if colors else [default_palette[i % len(default_palette)] for i in range(len(subject_names))]

    fig = go.Figure(data=[
        go.Bar(
            y=subject_names,
            x=hours_list,
            orientation='h',
            marker=dict(color=bar_colors),
            hovertemplate='<b>%{y}</b>: %{x:.1f} hours<extra></extra>',
        )
    ])
    layout = get_base_layout('Subject Time Investment (Hours)', height=max(220, len(subject_names) * 38))
    layout['margin']['l'] = 110
    fig.update_layout(layout)
    fig.update_xaxes(title_text='Hours', gridcolor=THEME['grid'], tickfont=dict(color=THEME['muted']))
    fig.update_yaxes(gridcolor=THEME['grid'], tickfont=dict(color=THEME['text']))
    return figure_to_html(fig)


def render_time_distribution_donut(labels, values, colors=None):
    """
    Donut chart representing percentage distribution of tracked time.
    """
    if not labels or not any(values):
        return figure_to_html(None, 'No tracked activity time available')

    default_palette = [THEME['indigo'], THEME['emerald'], THEME['sky'], THEME['purple'], THEME['amber'], THEME['pink'], THEME['rose']]
    slice_colors = colors if colors else [default_palette[i % len(default_palette)] for i in range(len(labels))]

    fig = go.Figure(data=[
        go.Pie(
            labels=labels,
            values=values,
            hole=0.55,
            marker=dict(colors=slice_colors),
            textinfo='label+percent',
            textfont=dict(family=FONT_FAMILY, size=11, color=THEME['text']),
            hovertemplate='<b>%{label}</b><br>%{value:.1f} hrs (%{percent})<extra></extra>',
        )
    ])
    layout = get_base_layout('Time Allocation Distribution', height=290)
    layout['showlegend'] = True
    fig.update_layout(layout)
    return figure_to_html(fig)


def render_habit_completion_chart(habit_names, completion_rates):
    """
    Horizontal progress-style bar chart of habit completion percentages.
    """
    if not habit_names:
        return figure_to_html(None, 'No active habits found in this period')

    # Color scale based on completion rate
    bar_colors = []
    for rate in completion_rates:
        if rate >= 80:
            bar_colors.append(THEME['emerald'])
        elif rate >= 50:
            bar_colors.append(THEME['amber'])
        else:
            bar_colors.append(THEME['rose'])

    fig = go.Figure(data=[
        go.Bar(
            y=habit_names,
            x=completion_rates,
            orientation='h',
            marker=dict(color=bar_colors),
            text=[f"{r:.0f}%" for r in completion_rates],
            textposition='auto',
            textfont=dict(color=THEME['text'], size=11),
            hovertemplate='<b>%{y}</b>: %{x:.1f}% completion<extra></extra>',
        )
    ])
    layout = get_base_layout('Habit Completion Rates', height=max(220, len(habit_names) * 40))
    layout['margin']['l'] = 110
    fig.update_layout(layout)
    fig.update_xaxes(range=[0, 105], title_text='Completion %', gridcolor=THEME['grid'], tickfont=dict(color=THEME['muted']))
    fig.update_yaxes(gridcolor=THEME['grid'], tickfont=dict(color=THEME['text']))
    return figure_to_html(fig)


def render_mood_sleep_trend_chart(dates, moods, sleeps, energies=None, stresses=None):
    """
    Multi-line trend chart showing daily mood, energy, and sleep duration.
    """
    if not dates or (not any(moods) and not any(sleeps)):
        return figure_to_html(None, 'No daily check-in or sleep data recorded')

    fig = make_subplots(specs=[[{"secondary_y": True}]])

    if any(m is not None for m in moods):
        fig.add_trace(
            go.Scatter(
                x=dates,
                y=moods,
                name='Mood (1-10)',
                mode='lines+markers',
                line=dict(color=THEME['emerald'], width=2.5),
                marker=dict(size=5),
                hovertemplate='Mood: %{y}/10<extra></extra>',
            ),
            secondary_y=False,
        )

    if energies and any(e is not None for e in energies):
        fig.add_trace(
            go.Scatter(
                x=dates,
                y=energies,
                name='Energy (1-10)',
                mode='lines+markers',
                line=dict(color=THEME['sky'], width=2),
                marker=dict(size=5),
                hovertemplate='Energy: %{y}/10<extra></extra>',
            ),
            secondary_y=False,
        )

    if stresses and any(s is not None for s in stresses):
        fig.add_trace(
            go.Scatter(
                x=dates,
                y=stresses,
                name='Stress (1-10)',
                mode='lines+markers',
                line=dict(color=THEME['rose'], width=1.8, dash='dot'),
                marker=dict(size=4),
                hovertemplate='Stress: %{y}/10<extra></extra>',
            ),
            secondary_y=False,
        )

    if any(s is not None for s in sleeps):
        fig.add_trace(
            go.Bar(
                x=dates,
                y=sleeps,
                name='Sleep Hours',
                marker_color=THEME['indigo'],
                opacity=0.35,
                hovertemplate='Sleep: %{y:.1f}h<extra></extra>',
            ),
            secondary_y=True,
        )

    layout = get_base_layout('Well-being Trends (Mood, Energy & Sleep)', height=320)
    fig.update_layout(layout)
    fig.update_xaxes(gridcolor=THEME['grid'], tickfont=dict(color=THEME['muted']))
    fig.update_yaxes(
        title_text='Score (1-10)',
        range=[0, 10.5],
        gridcolor=THEME['grid'],
        tickfont=dict(color=THEME['muted']),
        secondary_y=False
    )
    fig.update_yaxes(
        title_text='Sleep (Hours)',
        range=[0, 14],
        gridcolor='rgba(0,0,0,0)',
        tickfont=dict(color=THEME['muted']),
        secondary_y=True
    )
    return figure_to_html(fig)


def render_planned_vs_actual_chart(categories, planned_hours, actual_hours):
    """
    Grouped bar chart comparing planned vs actual duration.
    """
    if not categories or (not any(planned_hours) and not any(actual_hours)):
        return figure_to_html(None, 'No planned vs actual comparisons available')

    fig = go.Figure(data=[
        go.Bar(
            name='Planned Duration',
            x=categories,
            y=planned_hours,
            marker_color=THEME['indigo'],
            opacity=0.8,
            hovertemplate='Planned: %{y:.1f}h<extra></extra>',
        ),
        go.Bar(
            name='Actual Duration',
            x=categories,
            y=actual_hours,
            marker_color=THEME['emerald'],
            opacity=0.85,
            hovertemplate='Actual: %{y:.1f}h<extra></extra>',
        ),
    ])
    layout = get_base_layout('Planned vs Actual Duration (Hours)', height=290)
    layout['barmode'] = 'group'
    fig.update_layout(layout)
    fig.update_xaxes(gridcolor=THEME['grid'], tickfont=dict(color=THEME['muted']))
    fig.update_yaxes(title_text='Hours', gridcolor=THEME['grid'], tickfont=dict(color=THEME['muted']))
    return figure_to_html(fig)


def render_correlation_scatter_chart(x_vals, y_vals, x_label, y_label, title, r_score=None):
    """
    Scatter plot displaying paired observations with optional correlation indicator.
    """
    if not x_vals or not y_vals or len(x_vals) < 3:
        return figure_to_html(None, 'Insufficient data points for scatter visualization')

    chart_title = title
    if r_score is not None:
        chart_title += f" (Pearson r = {r_score:+.2f})"

    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=x_vals,
            y=y_vals,
            mode='markers',
            marker=dict(size=8, color=THEME['sky'], opacity=0.8, line=dict(color='#fff', width=0.5)),
            hovertemplate=f'{x_label}: %{{x}}<br>{y_label}: %{{y}}<extra></extra>',
        )
    )

    layout = get_base_layout(chart_title, height=280)
    fig.update_layout(layout)
    fig.update_xaxes(title_text=x_label, gridcolor=THEME['grid'], tickfont=dict(color=THEME['muted']))
    fig.update_yaxes(title_text=y_label, gridcolor=THEME['grid'], tickfont=dict(color=THEME['muted']))
    return figure_to_html(fig)


def render_finance_cashflow_chart(categories, amounts, types):
    """
    Bar chart showing expense and income distribution by category.
    """
    if not categories or not any(amounts):
        return figure_to_html(None, 'No financial transactions logged in this period')

    colors = [THEME['emerald'] if t == 'INCOME' else THEME['rose'] for t in types]

    fig = go.Figure(data=[
        go.Bar(
            x=categories,
            y=amounts,
            marker_color=colors,
            hovertemplate='<b>%{x}</b>: ₹%{y:,.2f}<extra></extra>',
        )
    ])
    layout = get_base_layout('Income vs Expenses by Category', height=280)
    fig.update_layout(layout)
    fig.update_xaxes(gridcolor=THEME['grid'], tickfont=dict(color=THEME['muted']))
    fig.update_yaxes(title_text='Amount (₹)', gridcolor=THEME['grid'], tickfont=dict(color=THEME['muted']))
    return figure_to_html(fig)
