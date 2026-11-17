"""Presentation primitives matching IDS_M1_Lab dashboard, without loading its runtime."""
from html import escape

COLORS = {'ok': '#27a884', 'warn': '#ed9851', 'bad': '#e05252', 'off': '#8a8f98', 'neutral': '#4c78a8'}


def badge(title, text, level):
    return (f"<div style='border-left:4px solid {COLORS[level]};padding:2px 10px;background:rgba(128,128,128,.08);border-radius:4px'>"
            f"<div style='font-size:.75rem;opacity:.7'>{escape(str(title))}</div><div style='font-weight:600'>{escape(str(text))}</div></div>")


def card(title, value, sub, level='neutral'):
    return (f"<div style='border-left:5px solid {COLORS[level]};padding:6px 12px;background:rgba(128,128,128,.08);border-radius:6px'>"
            f"<div style='font-size:.8rem;opacity:.75'>{escape(str(title))}</div>"
            f"<div style='font-size:1.9rem;font-weight:700;line-height:1.2'>{escape(str(value))}</div>"
            f"<div style='font-size:.75rem;opacity:.65'>{escape(str(sub))}</div></div>")


def paint(frame):
    def label_color(value):
        if value == 'Không hợp lệ':
            return 'background-color: rgba(138,143,152,.28)'
        return 'background-color: rgba(39,168,132,.28)' if value == 'Benign' else 'background-color: rgba(237,152,81,.40); font-weight: 600'
    return frame.style.map(label_color, subset=['Nhãn'])
