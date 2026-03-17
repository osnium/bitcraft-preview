from __future__ import annotations


def build_dark_stylesheet() -> str:
    return """
QWidget {
    background-color: #11151d;
    color: #e6edf7;
    font-family: "Segoe UI", "Candara", "Trebuchet MS";
    font-size: 10pt;
}
QFrame#MainSurface {
    background-color: #0e131b;
    border-radius: 12px;
}
QFrame#ContentSurface {
    background-color: #141b26;
    border: 1px solid #263246;
    border-radius: 12px;
}
QFrame#SidebarSurface {
    background-color: #131a25;
    border: 1px solid #263246;
    border-radius: 12px;
}
QFrame#GroupCard {
    background-color: #151f2d;
    border: 1px solid #2a384f;
    border-radius: 10px;
}
QLabel#SectionTitle {
    font-size: 12pt;
    font-weight: 600;
    color: #f8fbff;
    background-color: transparent;
}
QLabel#MutedText {
    color: #9caec7;
    background-color: transparent;
}
QPushButton {
    background-color: #1a2534;
    border: 1px solid #2b3a53;
    border-radius: 6px;
    padding: 6px 10px;
}
QPushButton:hover {
    background-color: #223048;
}
QPushButton:pressed {
    background-color: #162132;
}
QPushButton#SidebarToggle {
    background-color: #1a2534;
    border: 1px solid #2b3a53;
    border-radius: 6px;
    padding: 0px;
    min-width: 24px;
    max-width: 24px;
    min-height: 24px;
    max-height: 24px;
}
QPushButton#SidebarToggle:hover {
    background-color: #223048;
    border: 1px solid #355077;
}
QWidget#SidebarToggleRow {
    background-color: transparent;
    border: none;
}
QWidget#QuickActionsStrip {
    background-color: transparent;
}
QPushButton#QuickActionButton {
    background-color: #1a2534;
    border: 1px solid #2b3a53;
    border-radius: 7px;
    padding: 0px;
}
QPushButton#QuickActionButton:hover {
    background-color: #223048;
}
QPushButton#QuickActionButton:pressed {
    background-color: #162132;
}
QListWidget {
    background-color: transparent;
    border: none;
    outline: none;
}
QListWidget::item {
    margin: 2px 0;
    padding: 7px 8px;
    border-radius: 6px;
}
QListWidget::item:selected {
    background-color: #365375;
    color: #ffffff;
}
QListWidget::item:hover {
    background-color: #2c435f;
}
QSlider::groove:horizontal {
    border: none;
    background: #232b37;
    height: 8px;
    border-radius: 4px;
}
QSlider::handle:horizontal {
    background: #dfe8f8;
    border: 1px solid #a6b5cc;
    width: 14px;
    margin: -3px 0;
    border-radius: 7px;
}
QSlider::sub-page:horizontal {
    background: #49a5ff;
    border-radius: 4px;
}
QSlider::add-page:horizontal {
    background: #232b37;
    border-radius: 4px;
}
QTableWidget {
    background-color: #131c2a;
    border: 1px solid #2a384f;
    gridline-color: #27354a;
}
QHeaderView::section {
    background-color: #1b293b;
    color: #e7efff;
    border: 1px solid #2a3a52;
    padding: 6px;
}
QToolButton#SectionToggle {
    background-color: transparent;
    border: none;
    color: #d9e7f5;
    font-weight: 600;
    text-align: left;
    padding: 4px 2px;
}
QToolButton#SectionToggle:hover {
    color: #ffffff;
}
QFrame#SectionDivider {
    background-color: #2a384f;
    min-height: 1px;
}
QFrame#AccountRow {
    background-color: #162131;
    border: 1px solid #2a384f;
    border-radius: 9px;
}
QFrame#AccountRow:hover {
    border: 1px solid #365375;
    background-color: #18273a;
}
QFrame#AccountRow[selected="true"] {
    border: 1px solid #58a8ff;
    background-color: #1b2b40;
}
QLabel#AccountDisplayName {
    color: #f3f8ff;
    font-size: 10pt;
    font-weight: 600;
    background-color: transparent;
}
QLabel#AccountStatusDot {
    background-color: transparent;
}
QLabel#AccountRowStatus {
    color: #8fd0ff;
    font-size: 8.5pt;
    background-color: transparent;
}
QLabel#AccountRowStatus[error="true"] {
    color: #ff9c9c;
}
QPushButton#AccountActionButton,
QPushButton#AccountFooterButton {
    background-color: #1a2534;
    border: 1px solid #2b3a53;
    border-radius: 7px;
    padding: 0px;
}
QPushButton#AccountActionButton:hover,
QPushButton#AccountFooterButton:hover {
    background-color: #223048;
    border: 1px solid #4d79a8;
}
QPushButton#AccountActionButton:pressed,
QPushButton#AccountFooterButton:pressed {
    background-color: #162132;
}
QPushButton#AccountActionButton:disabled,
QPushButton#AccountFooterButton:disabled,
QPushButton#AccountInlineButton:disabled,
QPushButton#AccountsEmptyState:disabled {
    background-color: #101721;
    color: #68809f;
    border: 1px solid #1e2b3d;
}
QFrame#AccountInlineEditor {
    background-color: #101721;
    border: 1px solid #27354a;
    border-radius: 8px;
}
QPushButton#AccountInlineButton {
    background-color: #1a2534;
    border: 1px solid #2b3a53;
    border-radius: 6px;
    padding: 5px 10px;
}
QPushButton#AccountsEmptyState {
    background-color: #1a2534;
    border: 1px solid #2b3a53;
    border-radius: 6px;
    color: #d6e7fb;
    padding: 10px;
}
QPushButton#AccountsEmptyState:hover {
    background-color: #1f2f41;
    border: 1px solid #3a4d64;
}
QLabel#AccountFeedback {
    color: #9caec7;
    background-color: transparent;
}
QLabel#AccountFeedback[error="true"] {
    color: #ff8d8d;
}
QScrollBar:vertical {
    background: #121a27;
    width: 10px;
    margin: 0;
    border-radius: 5px;
}
QScrollBar::handle:vertical {
    background: #2e4059;
    min-height: 22px;
    border-radius: 5px;
}
QScrollBar::handle:vertical:hover {
    background: #395174;
}
QScrollBar::add-line:vertical,
QScrollBar::sub-line:vertical {
    height: 0;
}
QScrollBar::add-page:vertical,
QScrollBar::sub-page:vertical {
    background: transparent;
}
QScrollBar:horizontal {
    background: #121a27;
    height: 10px;
    margin: 0;
    border-radius: 5px;
}
QScrollBar::handle:horizontal {
    background: #2e4059;
    min-width: 22px;
    border-radius: 5px;
}
QScrollBar::handle:horizontal:hover {
    background: #395174;
}
QScrollBar::add-line:horizontal,
QScrollBar::sub-line:horizontal {
    width: 0;
}
QScrollBar::add-page:horizontal,
QScrollBar::sub-page:horizontal {
    background: transparent;
}
QFrame#UpdateBanner {
    background-color: #1c1a0d;
    border: 1px solid #4a4218;
    border-radius: 8px;
    padding: 2px 0px;
}
QLabel#UpdateBannerLabel {
    color: #f0d060;
    font-weight: 600;
    background-color: transparent;
}
QPushButton#UpdateBannerViewBtn {
    background-color: transparent;
    border: 1px solid #5a6a88;
    border-radius: 5px;
    color: #80c0ff;
    padding: 3px 10px;
    font-size: 9pt;
}
QPushButton#UpdateBannerViewBtn:hover {
    background-color: #1b2a40;
    border-color: #80c0ff;
}
QPushButton#UpdateBannerDismissBtn {
    background-color: transparent;
    border: none;
    color: #8a9ab5;
    font-size: 13pt;
    padding: 0px;
}
QPushButton#UpdateBannerDismissBtn:hover {
    color: #c0cfe8;
}
"""
