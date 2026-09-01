"""Dark, NitroSense-inspired stylesheet."""

BG = "#15181f"
PANEL = "#1d212b"
ACCENT = "#4fd1c5"
ACCENT_DIM = "#2a3a3a"
TEXT = "#e6e9ef"
TEXT_DIM = "#8b93a6"

STYLESHEET = f"""
QMainWindow, QWidget {{
    background-color: {BG};
    color: {TEXT};
    font-family: 'Segoe UI';
    font-size: 13px;
}}

#Sidebar {{
    background-color: {PANEL};
    border-right: 1px solid #262b36;
}}

#SidebarTitle {{
    color: {ACCENT};
    font-size: 16px;
    font-weight: 600;
    padding: 18px 16px;
}}

QFrame#Card {{
    background-color: {PANEL};
    border-radius: 12px;
}}

QLabel#MetricValue {{
    font-size: 26px;
    font-weight: 600;
    color: {TEXT};
}}

QLabel#MetricLabel {{
    color: {TEXT_DIM};
    font-size: 12px;
    letter-spacing: 1px;
}}

QPushButton#SidebarItem {{
    background-color: transparent;
    color: {TEXT};
    border-radius: 8px;
    padding: 10px 14px;
    border: none;
    text-align: left;
}}

QPushButton#SidebarItem:checked {{
    background-color: {ACCENT_DIM};
    color: {ACCENT};
    font-weight: 600;
}}

QPushButton#SidebarItem:hover {{
    background-color: #232833;
}}

QSlider::groove:horizontal {{
    height: 6px;
    background: #2a2f3a;
    border-radius: 3px;
}}

QSlider::handle:horizontal {{
    background: {ACCENT};
    width: 16px;
    margin: -6px 0;
    border-radius: 8px;
}}

QSlider::sub-page:horizontal {{
    background: {ACCENT};
    border-radius: 3px;
}}

QPushButton#FlatButton {{
    background-color: transparent;
    color: {TEXT_DIM};
    border: 1px solid #333a48;
    border-radius: 8px;
    padding: 6px 12px;
}}

QPushButton#FlatButton:hover {{
    color: {TEXT};
    border-color: {ACCENT};
}}
"""
