#!/usr/bin/env python3
"""
Survey Report Generator — WHU Open Campus Policy Research
=========================================================
Reads survey_responses.jsonl and produces a self-contained HTML report
with embedded charts (pie, bar, stacked bar, cross-tabulations).

Usage:
    python report_generator.py                          # default input
    python report_generator.py -i survey_responses.jsonl -o report.html
"""

import json
import os
import sys
import io
import base64
import argparse
from datetime import datetime
from collections import Counter, defaultdict
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
matplotlib.rcParams['font.sans-serif'] = ['SimHei', 'Microsoft YaHei', 'PingFang SC', 'DejaVu Sans']
matplotlib.rcParams['axes.unicode_minus'] = False
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker

HERE = Path(__file__).parent

# ============================================================
# CONFIGURATION
# ============================================================

# Color palette
C_BLUE_DARK  = '#1a5276'
C_BLUE       = '#2e86c1'
C_BLUE_LIGHT = '#5dade2'
C_BLUE_PALE  = '#aed6f1'
C_GREEN      = '#27ae60'
C_RED        = '#e74c3c'
C_ORANGE     = '#f39c12'
C_GRAY       = '#95a5a6'
C_GRAY_LIGHT = '#ecf0f1'

PALETTE_5 = [C_BLUE_DARK, C_BLUE, C_BLUE_LIGHT, C_BLUE_PALE, C_GRAY_LIGHT]
PALETTE_BLUE_GRADIENT = ['#0d3b66','#1a5276','#2471a3','#2e86c1','#5dade2','#85c1e9','#aed6f1']
PALETTE_DIVERGING = [C_RED, C_ORANGE, C_GRAY, C_BLUE_LIGHT, C_GREEN]
PALETTE_IDENTITY = ['#1a5276','#2e86c1','#5dade2','#f39c12','#e74c3c','#95a5a6']

# Question label mappings
IDENTITY_LABELS = {
    '武汉大学本科生': '本科生', '武汉大学研究生': '研究生',
    '武汉大学教职工': '教职工', '校友': '校友', '社会公众': '社会公众', '其他': '其他'
}

# ============================================================
# DATA LOADING
# ============================================================

def load_data(filepath):
    """Load JSONL survey responses."""
    responses = []
    if not os.path.exists(filepath):
        print(f'WARNING: Data file not found: {filepath}')
        return responses
    with open(filepath, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if line:
                try:
                    responses.append(json.loads(line))
                except json.JSONDecodeError:
                    continue
    return responses


def get_answer(resp, qid):
    """Extract answer for a question ID from a response."""
    return resp.get('answers', {}).get(qid)


def count_answers(responses, qid, filter_ua=True):
    """Count answer frequencies for a given question ID.
    Returns list of (label, count) tuples sorted by count descending.
    """
    counter = Counter()
    for r in responses:
        ans = get_answer(r, qid)
        if ans is None:
            continue
        if filter_ua and ans == '__UNABLE_TO_ANSWER__':
            continue
        if isinstance(ans, list):
            for item in ans:
                if not filter_ua or item != '__UNABLE_TO_ANSWER__':
                    counter[item] += 1
        else:
            counter[ans] += 1
    return counter.most_common()


def count_likert(responses, qid, labels):
    """Count Likert-scale responses in order."""
    counts = {l: 0 for l in labels}
    for r in responses:
        ans = get_answer(r, qid)
        if ans and ans in counts:
            counts[ans] += 1
    return [(l, counts[l]) for l in labels]


def count_ua(responses, qid):
    """Count 'unable to answer' responses."""
    count = 0
    for r in responses:
        ans = get_answer(r, qid)
        if ans == '__UNABLE_TO_ANSWER__' or (isinstance(ans, list) and '__UNABLE_TO_ANSWER__' in ans):
            count += 1
    return count


# ============================================================
# CHART GENERATION
# ============================================================

def fig_to_b64(fig, dpi=120):
    """Convert matplotlib figure to base64 PNG string."""
    buf = io.BytesIO()
    fig.savefig(buf, format='png', dpi=dpi, bbox_inches='tight', facecolor='white', edgecolor='none')
    buf.seek(0)
    b64 = base64.b64encode(buf.read()).decode()
    plt.close(fig)
    return f'data:image/png;base64,{b64}'


def make_pie(labels, values, title, colors=None, max_items=7):
    """Generate a donut-style pie chart. Returns base64 PNG."""
    if not labels or sum(values) == 0:
        return None

    # Truncate to max_items, group rest as "其他"
    if len(labels) > max_items:
        labels = list(labels[:max_items])
        values = list(values[:max_items])

    if colors is None:
        colors = PALETTE_BLUE_GRADIENT[:len(labels)]

    fig, ax = plt.subplots(figsize=(7, 5))
    wedges, texts, autotexts = ax.pie(
        values, labels=None, colors=colors,
        autopct='%1.1f%%', pctdistance=0.75,
        startangle=90, wedgeprops={'width': 0.45, 'edgecolor': 'white', 'linewidth': 1.5}
    )
    for at in autotexts:
        at.set_fontsize(10)
        at.set_fontweight('bold')

    ax.legend(wedges, [f'{l} ({v})' for l, v in zip(labels, values)],
              loc='center left', bbox_to_anchor=(1, 0.5), fontsize=9, frameon=False)
    ax.set_title(title, fontsize=14, fontweight='bold', color=C_BLUE_DARK, pad=16)
    return fig_to_b64(fig)


def make_bar(labels, values, title, xlabel='', color=C_BLUE, horizontal=True):
    """Generate a horizontal bar chart. Returns base64 PNG."""
    if not labels or sum(values) == 0:
        return None

    fig, ax = plt.subplots(figsize=(8, max(3.5, len(labels) * 0.5)))
    y_pos = range(len(labels))
    bars = ax.barh(y_pos, values, height=0.6, color=color, edgecolor='white', linewidth=0.5)

    # Add value labels
    for bar, val in zip(bars, values):
        ax.text(bar.get_width() + max(values) * 0.02, bar.get_y() + bar.get_height() / 2,
                str(val), va='center', fontsize=10, fontweight='bold', color=C_BLUE_DARK)

    ax.set_yticks(y_pos)
    ax.set_yticklabels(labels, fontsize=10)
    ax.set_xlabel(xlabel, fontsize=10, color=C_GRAY)
    ax.set_title(title, fontsize=13, fontweight='bold', color=C_BLUE_DARK, pad=12)
    ax.set_xlim(0, max(values) * 1.25)
    ax.invert_yaxis()
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    ax.spines['left'].set_color('#e0e0e0')
    ax.spines['bottom'].set_color('#e0e0e0')
    ax.tick_params(colors=C_GRAY, which='both')
    ax.xaxis.set_major_locator(mticker.MaxNLocator(integer=True))

    return fig_to_b64(fig)


def make_stacked_bar(categories, series_data, title, series_colors=None):
    """Generate a horizontal stacked bar chart (for Likert scales).
    series_data: list of (label, values_list) tuples
    categories: list of category names
    """
    if not categories:
        return None

    fig, ax = plt.subplots(figsize=(9, max(3.5, len(categories) * 0.5)))
    y_pos = range(len(categories))

    if series_colors is None:
        series_colors = PALETTE_DIVERGING[:len(series_data)]

    left = [0] * len(categories)
    for i, (slabel, svalues) in enumerate(series_data):
        bars = ax.barh(y_pos, svalues, left=left, height=0.55,
                       color=series_colors[i], label=slabel, edgecolor='white', linewidth=0.5)
        # Add percentage labels for significant segments
        for j, (bar, val) in enumerate(zip(bars, svalues)):
            total = sum(svl[j] for _, svl in series_data)
            if total > 0 and val / total > 0.08:
                ax.text(left[j] + val / 2, bar.get_y() + bar.get_height() / 2,
                        f'{val}', ha='center', va='center', fontsize=8, fontweight='bold')
        left = [l + v for l, v in zip(left, svalues)]

    ax.set_yticks(y_pos)
    ax.set_yticklabels(categories, fontsize=10)
    ax.set_title(title, fontsize=13, fontweight='bold', color=C_BLUE_DARK, pad=12)
    ax.legend(loc='lower right', fontsize=9, frameon=False)
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    ax.spines['left'].set_color('#e0e0e0')
    ax.spines['bottom'].set_color('#e0e0e0')
    ax.tick_params(colors=C_GRAY)
    ax.xaxis.set_major_locator(mticker.MaxNLocator(integer=True))

    return fig_to_b64(fig)


def make_histogram(values, title, xlabel='', bins=6, color=C_BLUE):
    """Generate a histogram (for age distribution)."""
    if not values:
        return None

    fig, ax = plt.subplots(figsize=(7, 4))
    ax.hist(values, bins=bins, color=color, edgecolor='white', linewidth=1.2, alpha=0.85)
    ax.set_xlabel(xlabel, fontsize=10, color=C_GRAY)
    ax.set_ylabel('人数', fontsize=10, color=C_GRAY)
    ax.set_title(title, fontsize=13, fontweight='bold', color=C_BLUE_DARK, pad=12)
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    ax.spines['left'].set_color('#e0e0e0')
    ax.spines['bottom'].set_color('#e0e0e0')
    ax.tick_params(colors=C_GRAY)
    ax.yaxis.set_major_locator(mticker.MaxNLocator(integer=True))
    return fig_to_b64(fig)


def make_grouped_bar(categories, groups, title, group_colors=None):
    """Generate a grouped bar chart for cross-tabulation.
    groups: list of (group_name, values_list) tuples
    categories: list of category labels
    """
    if not categories:
        return None

    n_groups = len(groups)
    n_cats = len(categories)
    bar_width = 0.7 / n_groups

    fig, ax = plt.subplots(figsize=(max(8, n_cats * 1.2), 5))
    x = range(n_cats)

    if group_colors is None:
        group_colors = PALETTE_IDENTITY[:n_groups]

    for i, (gname, gvalues) in enumerate(groups):
        offset = (i - (n_groups - 1) / 2) * bar_width
        ax.bar([xi + offset for xi in x], gvalues, bar_width * 0.9,
               label=gname, color=group_colors[i], edgecolor='white', linewidth=0.5)

    ax.set_xticks(x)
    ax.set_xticklabels(categories, fontsize=9, rotation=25, ha='right')
    ax.set_title(title, fontsize=13, fontweight='bold', color=C_BLUE_DARK, pad=12)
    ax.legend(fontsize=9, frameon=False)
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    ax.spines['left'].set_color('#e0e0e0')
    ax.spines['bottom'].set_color('#e0e0e0')
    ax.tick_params(colors=C_GRAY)
    ax.yaxis.set_major_locator(mticker.MaxNLocator(integer=True))
    return fig_to_b64(fig)


# ============================================================
# ANALYSIS HELPERS
# ============================================================

def split_by_identity(responses):
    """Split responses by identity group."""
    groups = defaultdict(list)
    for r in responses:
        identity = get_answer(r, 'Q1')
        if identity and identity != '__UNABLE_TO_ANSWER__':
            groups[identity].append(r)
    return dict(groups)


def cross_tab(responses, row_qid, col_qid, row_labels, col_labels):
    """Build a cross-tabulation matrix. Returns {row_label: {col_label: count}}."""
    matrix = {rl: {cl: 0 for cl in col_labels} for rl in row_labels}
    for r in responses:
        row_val = get_answer(r, row_qid)
        col_val = get_answer(r, col_qid)
        if row_val in matrix and col_val in matrix[row_val]:
            matrix[row_val][col_val] += 1
    return matrix


# ============================================================
# REPORT HTML GENERATION
# ============================================================

CSS = '''
<style>
  * { box-sizing: border-box; margin: 0; padding: 0; }
  body { font-family: -apple-system, "PingFang SC", "Microsoft YaHei", "Segoe UI", sans-serif;
         background: #f5f6fa; color: #2c3e50; line-height: 1.8; }
  .report { max-width: 860px; margin: 0 auto; padding: 20px; }

  /* Cover */
  .cover { background: linear-gradient(135deg, #1a5276 0%, #2e86c1 100%); color: #fff;
           border-radius: 14px; padding: 60px 40px; text-align: center; margin-bottom: 32px; }
  .cover h1 { font-size: 28px; font-weight: 800; margin-bottom: 8px; }
  .cover .subtitle { font-size: 16px; opacity: 0.85; margin-bottom: 24px; }
  .cover .meta { font-size: 13px; opacity: 0.7; }
  .cover .meta span { margin: 0 12px; }

  /* Section */
  .section { background: #fff; border-radius: 12px; padding: 32px 28px; margin-bottom: 24px;
             box-shadow: 0 1px 4px rgba(0,0,0,.04); }
  .section h2 { font-size: 20px; color: #1a5276; border-bottom: 3px solid #2e86c1;
                padding-bottom: 10px; margin-bottom: 20px; }
  .section h3 { font-size: 16px; color: #2c3e50; margin: 24px 0 12px; }

  /* Stat tiles */
  .stat-row { display: flex; gap: 16px; flex-wrap: wrap; margin-bottom: 20px; }
  .stat-tile { flex: 1; min-width: 120px; background: #f8fafc; border-radius: 10px;
               padding: 18px 16px; text-align: center; border: 1px solid #e8ecf1; }
  .stat-tile .num { font-size: 32px; font-weight: 800; color: #1a5276; }
  .stat-tile .lbl { font-size: 12px; color: #95a5a6; margin-top: 4px; }

  /* Chart */
  .chart-block { margin: 20px 0; text-align: center; }
  .chart-block img { max-width: 100%; height: auto; border-radius: 6px; }
  .chart-block .caption { font-size: 12px; color: #95a5a6; margin-top: 6px; }

  /* Tables */
  table { width: 100%; border-collapse: collapse; margin: 12px 0; font-size: 13px; }
  th { background: #f0f4f8; color: #1a5276; font-weight: 700;
       padding: 10px 12px; text-align: left; border-bottom: 2px solid #d5dde5; }
  td { padding: 9px 12px; border-bottom: 1px solid #eef1f5; }
  tr:hover td { background: #fafcfd; }

  /* Quotes */
  .quote-block { background: #fef9e7; border-left: 4px solid #f39c12; padding: 14px 18px;
                 margin: 10px 0; border-radius: 0 8px 8px 0; font-size: 14px; color: #7d6608; }
  .quote-block .author { font-size: 12px; color: #b7950b; margin-top: 6px; }

  /* TOC */
  .toc { list-style: none; padding: 0; }
  .toc li { padding: 4px 0; }
  .toc a { color: #2e86c1; text-decoration: none; font-size: 14px; }
  .toc a:hover { text-decoration: underline; }

  /* Footer */
  .footer { text-align: center; padding: 24px; color: #95a5a6; font-size: 12px; }

  @media print {
    body { background: #fff; }
    .section { box-shadow: none; border: 1px solid #eee; page-break-inside: avoid; }
    .cover { -webkit-print-color-adjust: exact; print-color-adjust: exact; }
  }
  @media (max-width: 640px) {
    .cover { padding: 32px 20px; }
    .cover h1 { font-size: 22px; }
    .section { padding: 20px 16px; }
    .stat-tile { min-width: 80px; }
  }
</style>
'''


def build_report(responses, output_path):
    """Generate the complete HTML report."""
    total = len(responses)
    charts = []  # collect (section_id, title, b64_img) tuples

    # --- Demographics ---
    identity_counts = count_answers(responses, 'Q1')
    identity_labels = [IDENTITY_LABELS.get(l, l) for l, _ in identity_counts]
    identity_values = [v for _, v in identity_counts]

    age_values = []
    for r in responses:
        ans = get_answer(r, 'Q2')
        if ans:
            try:
                age = int(ans)
                if 1 <= age <= 120:
                    age_values.append(age)
            except (ValueError, TypeError):
                pass

    gender_counts = count_answers(responses, 'Q3')

    q4_counts = count_answers(responses, 'Q4')
    visited_before = sum(v for l, v in q4_counts if l == '是')
    not_visited = sum(v for l, v in q4_counts if l == '否')

    # Charts
    pie_identity = make_pie(identity_labels, identity_values, '受访者身份分布')
    pie_gender = make_pie([l for l, _ in gender_counts], [v for _, v in gender_counts],
                          '性别分布', colors=[C_BLUE_DARK, C_BLUE_LIGHT, C_GRAY_LIGHT])
    hist_age = make_histogram(age_values, '年龄分布', xlabel='年龄', bins=min(8, len(set(age_values))), color=C_BLUE)

    # --- Dimension A: Order ---
    a1 = count_answers(responses, 'A1')
    a2 = count_likert(responses, 'A2', ['非常差', '较差', '一般', '较好', '非常好'])
    a3 = count_answers(responses, 'A3')
    a4 = count_answers(responses, 'A4')

    # --- Dimension B: Attitude ---
    b1 = count_answers(responses, 'B1')
    b2 = count_likert(responses, 'B2', ['非常不同意', '不同意', '一般', '同意', '非常同意'])
    b3 = count_answers(responses, 'B3')

    # --- Dimension C: Experience ---
    c1 = count_answers(responses, 'C1')
    c2 = count_answers(responses, 'C2')
    c3 = count_answers(responses, 'C3')

    # --- Dimension D: Management ---
    d1 = count_likert(responses, 'D1', ['很不足', '不足', '一般', '较好', '很好'])
    d2 = count_answers(responses, 'D2')
    d3 = count_answers(responses, 'D3')

    # --- Dimension E: Public Perspective ---
    e1 = count_answers(responses, 'E1')
    e2 = count_answers(responses, 'E2')

    # --- Dimension F: Overall ---
    f1 = count_answers(responses, 'F1')
    f2 = count_answers(responses, 'F2')
    f3 = count_likert(responses, 'F3', ['非常消极', '较消极', '一般', '较积极', '非常积极'])

    # --- Cross analysis ---
    identity_groups = split_by_identity(responses)
    # B1 by identity
    b1_labels = ['非常支持', '比较支持', '一般', '不太支持', '完全不支持']
    main_identities = ['武汉大学本科生', '武汉大学研究生', '社会公众', '校友']
    cross_b1_groups = []
    for ident in main_identities:
        if ident in identity_groups:
            counts = count_answers(identity_groups[ident], 'B1')
            cmap = {l: 0 for l in b1_labels}
            for l, c in counts:
                if l in cmap:
                    cmap[l] = c
            cross_b1_groups.append((IDENTITY_LABELS.get(ident, ident), [cmap[l] for l in b1_labels]))

    # F1 by identity
    f1_labels = ['利大于弊', '略利于弊', '利弊相当', '略弊于利', '弊大于利']
    cross_f1_groups = []
    for ident in main_identities:
        if ident in identity_groups:
            counts = count_answers(identity_groups[ident], 'F1')
            cmap = {l: 0 for l in f1_labels}
            for l, c in counts:
                if l in cmap:
                    cmap[l] = c
            cross_f1_groups.append((IDENTITY_LABELS.get(ident, ident), [cmap[l] for l in f1_labels]))

    # --- Generate all charts ---
    def add_chart(sec, title, fn, *args):
        try:
            img = fn(*args)
            if img:
                charts.append((sec, title, img))
        except Exception as e:
            print(f'  WARNING: Chart "{title}" failed: {e}')

    sec = 'demographics'
    add_chart(sec, '受访者身份分布', make_pie, identity_labels, identity_values, '受访者身份分布')
    add_chart(sec, '性别分布', make_pie, [l for l,_ in gender_counts], [v for _,v in gender_counts], '性别分布', [C_BLUE_DARK, C_BLUE_LIGHT, C_GRAY_LIGHT])
    add_chart(sec, '年龄分布', make_histogram, age_values, '年龄分布', '年龄')

    sec = 'order'
    add_chart(sec, 'A1-人流量变化感知', make_bar, [l for l,_ in a1], [v for _,v in a1], '校园人流量变化感知 (A1)', '人数')
    if any(v for _,v in a2):
        add_chart(sec, 'A2-校园秩序评价', make_stacked_bar,
                  [l for l,_ in a2],
                  [('评价', [v for _,v in a2])],
                  '校园整体秩序评价 (A2)',
                  [C_RED, C_ORANGE, C_GRAY, C_BLUE_LIGHT, C_GREEN])
    add_chart(sec, 'A3-干扰频率', make_bar, [l for l,_ in a3], [v for _,v in a3], '外来人员干扰频率 (A3)', '人数')
    if a4:
        add_chart(sec, 'A4-干扰类型', make_bar, [l for l,_ in a4], [v for _,v in a4], '干扰主要体现方面 (A4, 多选)', '被选次数')

    sec = 'attitude'
    add_chart(sec, 'B1-政策支持度', make_bar, [l for l,_ in b1], [v for _,v in b1], '对开放政策的支持度 (B1)', '人数')
    if any(v for _,v in b2):
        add_chart(sec, 'B2-开放功能认同', make_stacked_bar,
                  [l for l,_ in b2], [('认同度', [v for _,v in b2])],
                  '大学应承担社会开放功能吗 (B2)',
                  [C_RED, C_ORANGE, C_GRAY, C_BLUE_LIGHT, C_GREEN])
    add_chart(sec, 'B3-优先解决问题', make_bar, [l for l,_ in b3], [v for _,v in b3], '最希望优先解决的问题 (B3)', '人数')

    sec = 'experience'
    add_chart(sec, 'C1-频率变化', make_bar, [l for l,_ in c1], [v for _,v in c1], '进入校园频率变化 (C1)', '人数')
    if c2:
        add_chart(sec, 'C2-环境变化', make_bar, [l for l,_ in c2], [v for _,v in c2], '校园环境相比开放前 (C2)', '人数')
    add_chart(sec, 'C3-时段感知', make_bar, [l for l,_ in c3], [v for _,v in c3], '影响最明显的时段 (C3)', '人数')

    sec = 'management'
    if any(v for _,v in d1):
        add_chart(sec, 'D1-管理力度', make_stacked_bar,
                  [l for l,_ in d1], [('评价', [v for _,v in d1])],
                  '校园管理力度评价 (D1)',
                  [C_RED, C_ORANGE, C_GRAY, C_BLUE_LIGHT, C_GREEN])
    if d2:
        add_chart(sec, 'D2-观察到的现象', make_bar, [l for l,_ in d2], [v for _,v in d2], '校园内观察到的现象 (D2, 多选)', '被选次数')
    if d3:
        add_chart(sec, 'D3-需加强的方面', make_bar, [l for l,_ in d3], [v for _,v in d3], '最需要加强的管理方面 (D3, 多选)', '被选次数')

    sec = 'public'
    if e1:
        add_chart(sec, 'E1-来访目的', make_bar, [l for l,_ in e1], [v for _,v in e1], '校外访客来校主要目的 (E1)', '人数')
    if e2:
        add_chart(sec, 'E2-观察公众行为', make_bar, [l for l,_ in e2], [v for _,v in e2], '校内人员观察到的公众行为 (E2, 多选)', '被选次数')

    sec = 'overall'
    add_chart(sec, 'F1-总体影响', make_bar, [l for l,_ in f1], [v for _,v in f1], '开放政策的总体影响评价 (F1)', '人数')
    add_chart(sec, 'F2-是否保持', make_bar, [l for l,_ in f2], [v for _,v in f2], '是否希望保持现行模式 (F2)', '人数')
    if any(v for _,v in f3):
        add_chart(sec, 'F3-城市形象', make_stacked_bar,
                  [l for l,_ in f3], [('评价', [v for _,v in f3])],
                  '开放对武汉城市形象的影响 (F3)',
                  [C_RED, C_ORANGE, C_GRAY, C_BLUE_LIGHT, C_GREEN])

    sec = 'cross'
    if cross_b1_groups and len(cross_b1_groups) >= 2:
        add_chart(sec, '交叉-身份×政策支持', make_grouped_bar, b1_labels, cross_b1_groups, '不同身份群体对开放政策的支持度 (B1 × 身份)')
    if cross_f1_groups and len(cross_f1_groups) >= 2:
        add_chart(sec, '交叉-身份×总体影响', make_grouped_bar, f1_labels, cross_f1_groups, '不同身份群体对总体影响的评价 (F1 × 身份)')

    # --- Open-ended responses ---
    g1_texts = []
    g2_texts = []
    for r in responses:
        g1 = get_answer(r, 'G1')
        g2 = get_answer(r, 'G2')
        if g1 and str(g1).strip():
            g1_texts.append(str(g1).strip())
        if g2 and str(g2).strip():
            g2_texts.append(str(g2).strip())

    # --- Build HTML ---
    sections = {
        'demographics': '一、受访者画像',
        'order': '二、校园秩序感受（A维度）',
        'attitude': '三、政策态度（B维度）',
        'experience': '四、实际体验（C维度）',
        'management': '五、安全管理（D维度）',
        'public': '六、公众视角（E维度）',
        'overall': '七、综合评价（F维度）',
        'cross': '八、交叉分析',
        'open': '九、开放题汇总',
        'conclusion': '十、结论与建议',
    }

    # Group charts by section
    chart_by_section = defaultdict(list)
    for sec_id, title, img in charts:
        chart_by_section[sec_id].append((title, img))

    # Build TOC
    toc_html = '<ul class="toc">'
    for sec_id in ['demographics','order','attitude','experience','management','public','overall','cross','open','conclusion']:
        if sec_id in sections:
            toc_html += f'<li><a href="#{sec_id}">{sections[sec_id]}</a></li>'
    toc_html += '</ul>'

    # Build section HTML
    sections_html = ''

    # Demographics
    sections_html += f'''
    <div class="section" id="demographics">
      <h2>{sections['demographics']}</h2>
      <div class="stat-row">
        <div class="stat-tile"><div class="num">{total}</div><div class="lbl">有效问卷</div></div>
        <div class="stat-tile"><div class="num">{len(identity_counts)}</div><div class="lbl">身份类型</div></div>
        <div class="stat-tile"><div class="num">{visited_before}</div><div class="lbl">开放前来过</div></div>
        <div class="stat-tile"><div class="num">{not_visited}</div><div class="lbl">开放后首次来</div></div>
      </div>
      <h3>身份构成</h3>
      <table><tr><th>身份</th><th>人数</th><th>占比</th></tr>
      {''.join(f'<tr><td>{IDENTITY_LABELS.get(l,l)}</td><td>{v}</td><td>{v/total*100:.1f}%</td></tr>' for l,v in identity_counts)}
      </table>
      <h3>年龄分布</h3>
      <p>平均年龄: {sum(age_values)/len(age_values):.1f} 岁 &nbsp;|&nbsp; 中位数: {sorted(age_values)[len(age_values)//2] if age_values else 'N/A'} 岁 &nbsp;|&nbsp; 范围: {min(age_values) if age_values else 'N/A'} — {max(age_values) if age_values else 'N/A'} 岁</p>
    '''

    # Charts for each section
    for sec_id in ['demographics','order','attitude','experience','management','public','overall']:
        if sec_id != 'demographics':
            sections_html += f'<div class="section" id="{sec_id}"><h2>{sections[sec_id]}</h2>'
        for title, img in chart_by_section.get(sec_id, []):
            sections_html += f'<div class="chart-block"><img src="{img}" alt="{title}"><div class="caption">{title}</div></div>'
        if sec_id != 'demographics':
            sections_html += '</div>'

    # Cross analysis
    if chart_by_section.get('cross'):
        sections_html += f'<div class="section" id="cross"><h2>{sections["cross"]}</h2>'
        for title, img in chart_by_section['cross']:
            sections_html += f'<div class="chart-block"><img src="{img}" alt="{title}"><div class="caption">{title}</div></div>'
        sections_html += '</div>'

    # Open-ended responses
    sections_html += f'<div class="section" id="open"><h2>{sections["open"]}</h2>'
    sections_html += f'<p>共收集到 <strong>{len(g1_texts)}</strong> 条"最大变化"描述和 <strong>{len(g2_texts)}</strong> 条建议。</p>'

    if g1_texts:
        sections_html += '<h3>主要变化感知（G1 · 代表性回答）</h3>'
        for t in g1_texts[:12]:
            sections_html += f'<div class="quote-block">{t}</div>'

    if g2_texts:
        sections_html += '<h3>具体建议（G2 · 代表性回答）</h3>'
        for t in g2_texts[:12]:
            sections_html += f'<div class="quote-block">{t}</div>'

    sections_html += '</div>'

    # Key findings (auto-generated based on data)
    findings = []
    # B1 analysis
    support_count = sum(v for l, v in b1 if l in ['非常支持', '比较支持'])
    oppose_count = sum(v for l, v in b1 if l in ['不太支持', '完全不支持'])
    b1_total = sum(v for _, v in b1)
    if b1_total > 0:
        if support_count / b1_total > 0.5:
            findings.append(f'多数受访者（{support_count}/{b1_total}，{support_count/b1_total*100:.0f}%）对开放政策持支持态度。')
        if oppose_count / b1_total > 0.3:
            findings.append(f'值得注意的是，{oppose_count/b1_total*100:.0f}% 的受访者表示不太支持或完全不支持当前开放政策。')

    # F1 analysis
    positive = sum(v for l, v in f1 if l in ['利大于弊', '略利于弊'])
    negative = sum(v for l, v in f1 if l in ['弊大于利', '略弊于利'])
    f1_total = sum(v for _, v in f1)
    if f1_total > 0:
        findings.append(f'总体来看，{positive/f1_total*100:.0f}% 的受访者认为开放政策利大于弊或略利于弊，{negative/f1_total*100:.0f}% 认为弊大于利或略弊于利。')

    # A3 analysis
    disturb_total = sum(v for l, v in a3 if l in ['经常', '偶尔'])
    a3_total = sum(v for _, v in a3)
    if a3_total > 0 and disturb_total / a3_total > 0.4:
        findings.append(f'{disturb_total/a3_total*100:.0f}% 的受访者表示曾受到外来人员干扰（"经常"或"偶尔"），说明管理层面仍有提升空间。')

    # D3 top concern
    if d3:
        top_concern = d3[0]
        findings.append(f'在管理改进方面，受访者最关注的是"{top_concern[0]}"（{top_concern[1]}人次选择）。')

    findings_html = ''.join(f'<li>{f}</li>' for f in findings)

    sections_html += f'''
    <div class="section" id="conclusion">
      <h2>{sections['conclusion']}</h2>
      <h3>主要发现</h3>
      <ol style="padding-left:20px;line-height:2.2;">{findings_html}</ol>
      <h3 style="margin-top:24px">研究说明</h3>
      <p style="font-size:14px;color:#666;">
        本报告基于 {total} 份有效问卷自动生成。问卷采用分层随机抽题设计（A~F六维度各抽1题），
        每题样本量因抽题概率不同而存在差异。图表中的"无法回答"选项已从统计中剔除。
        开放题回答为原始数据，未经编辑。<br><br>
        报告生成时间：{datetime.now().strftime('%Y年%m月%d日 %H:%M')}
      </p>
    </div>
    '''

    # Assemble full HTML
    html = f'''<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>武汉大学开放入校政策影响 · 调研报告</title>
{CSS}
</head>
<body>
<div class="report">

<div class="cover">
  <h1>武汉大学开放入校政策影响</h1>
  <div class="subtitle">调查研究报告</div>
  <div class="meta">
    <span>有效问卷: {total} 份</span>
    <span>调研时间: 2026年7月</span>
    <span>匿名调研</span>
  </div>
</div>

<div class="section">
  <h2>目录</h2>
  {toc_html}
</div>

{sections_html}

<div class="footer">
  武汉大学开放入校政策影响调研 · 匿名学术调研报告 · 自动生成于 {datetime.now().strftime('%Y-%m-%d')}
</div>

</div>
</body>
</html>'''

    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(html)

    print(f'Report saved to: {output_path}')
    print(f'  Total responses: {total}')
    print(f'  Charts generated: {len(charts)}')
    print(f'  Open-ended G1: {len(g1_texts)} responses')
    print(f'  Open-ended G2: {len(g2_texts)} responses')
    return output_path


# ============================================================
# MAIN
# ============================================================

def main():
    parser = argparse.ArgumentParser(description='Generate survey analysis report')
    parser.add_argument('-i', '--input', default=str(HERE / 'survey_responses.jsonl'),
                        help='Input JSONL file (default: survey_responses.jsonl)')
    parser.add_argument('-o', '--output', default=str(HERE / 'report.html'),
                        help='Output HTML file (default: report.html)')
    args = parser.parse_args()

    responses = load_data(args.input)
    if not responses:
        print('ERROR: No responses found. Please collect some survey data first.')
        print('You can test with sample data using: python report_generator.py -i sample_data.jsonl')
        sys.exit(1)

    build_report(responses, args.output)


if __name__ == '__main__':
    main()
