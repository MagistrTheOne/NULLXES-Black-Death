"""NULLXES BLACKBOX main menu — hangar art + centered product UI."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QDragEnterEvent, QDropEvent, QPainter
from PySide6.QtWidgets import QHBoxLayout, QLabel, QPushButton, QVBoxLayout, QWidget

from ..audio.playlist import AUDIO_EXTS
from ..config.settings import UserSettings
from ..i18n import lang, t
from .backdrop import paint_menu_art
from .theme import scale_px


class MainMenuView(QWidget):
    start = Signal()
    free_flight = Signal()
    training = Signal()
    aircraft = Signal()
    mission = Signal()
    settings = Signal()
    exit_app = Signal()
    language = Signal(str)
    tracks_dropped = Signal(list)

    def __init__(self, settings: UserSettings, version: str, parent=None) -> None:
        super().__init__(parent)
        self.cfg = settings
        self.version = version
        self.setAutoFillBackground(False)
        self.setAcceptDrops(True)

        root = QVBoxLayout(self)
        root.setContentsMargins(48, 36, 48, 28)

        lang_row = QHBoxLayout()
        lang_row.addStretch(1)
        self.btn_ru = QPushButton("RU")
        self.btn_en = QPushButton("EN")
        self.btn_ru.setObjectName("GhostBtn")
        self.btn_en.setObjectName("GhostBtn")
        self.btn_ru.clicked.connect(lambda: self.language.emit("ru"))
        self.btn_en.clicked.connect(lambda: self.language.emit("en"))
        lang_row.addWidget(self.btn_ru)
        lang_row.addWidget(self.btn_en)
        root.addLayout(lang_row)
        root.addStretch(2)

        col = QVBoxLayout()
        col.setAlignment(Qt.AlignHCenter)
        col.setSpacing(8)
        self.brand = QLabel("NULLXES")
        self.brand.setObjectName("Brand")
        self.brand.setAlignment(Qt.AlignCenter)
        self.title = QLabel("BLACKBOX")
        self.title.setObjectName("Title")
        self.title.setAlignment(Qt.AlignCenter)
        self.sub = QLabel("")
        self.sub.setObjectName("Muted")
        self.sub.setAlignment(Qt.AlignCenter)
        col.addWidget(self.brand)
        col.addWidget(self.title)
        col.addWidget(self.sub)
        col.addSpacing(28)
        self.btn_start = self._btn("", primary=True)
        self.btn_train = self._btn("")
        self.btn_ops = self._btn("")
        self.btn_ac = self._btn("")
        self.btn_st = self._btn("")
        self.btn_ex = self._btn("")
        self.btn_start.clicked.connect(self.free_flight.emit)
        self.btn_train.clicked.connect(self.training.emit)
        self.btn_ops.clicked.connect(self.mission.emit)
        self.btn_ac.clicked.connect(self.aircraft.emit)
        self.btn_st.clicked.connect(self.settings.emit)
        self.btn_ex.clicked.connect(self.exit_app.emit)
        for b in (self.btn_start, self.btn_train, self.btn_ops, self.btn_ac, self.btn_st, self.btn_ex):
            col.addWidget(b, 0, Qt.AlignHCenter)
        root.addLayout(col)
        root.addStretch(2)

        self.drop_hint = QLabel("")
        self.drop_hint.setObjectName("Muted")
        self.drop_hint.setAlignment(Qt.AlignCenter)
        self.now_playing = QLabel("")
        self.now_playing.setObjectName("Muted")
        self.now_playing.setAlignment(Qt.AlignCenter)
        self.status = QLabel()
        self.status.setObjectName("Muted")
        self.status.setAlignment(Qt.AlignCenter)
        self.build = QLabel(f"BUILD {version}")
        self.build.setObjectName("Muted")
        self.build.setAlignment(Qt.AlignCenter)
        root.addWidget(self.drop_hint)
        root.addWidget(self.now_playing)
        root.addWidget(self.status)
        root.addWidget(self.build)
        self.retranslate()
        self.relayout()

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        paint_menu_art(self, painter, left_vignette=False, dim=0.12)
        painter.end()
        super().paintEvent(event)

    def dragEnterEvent(self, event: QDragEnterEvent) -> None:
        if self._audio_urls(event.mimeData()):
            event.acceptProposedAction()

    def dropEvent(self, event: QDropEvent) -> None:
        paths = self._audio_urls(event.mimeData())
        if paths:
            self.tracks_dropped.emit(paths)
            event.acceptProposedAction()

    def _audio_urls(self, mime) -> list[str]:
        if mime is None or not mime.hasUrls():
            return []
        out: list[str] = []
        for url in mime.urls():
            path = Path(url.toLocalFile())
            if path.suffix.lower() in AUDIO_EXTS and path.is_file():
                out.append(str(path))
        return out

    def _btn(self, text: str, primary: bool = False) -> QPushButton:
        b = QPushButton(text)
        b.setObjectName("PrimaryBtn" if primary else "MenuBtn")
        b.setCursor(Qt.PointingHandCursor)
        return b

    def retranslate(self) -> None:
        self.sub.setText(t("drone_sim"))
        self.btn_start.setText(t("free_flight"))
        self.btn_train.setText(t("flight_training"))
        self.btn_ops.setText(t("operations"))
        self.btn_ac.setText(t("aircraft"))
        self.btn_st.setText(t("settings"))
        self.btn_ex.setText(t("exit"))
        self.drop_hint.setText(t("drop_music"))
        cur = lang()
        self.btn_ru.setStyleSheet("font-weight:600;" if cur == "ru" else "")
        self.btn_en.setStyleSheet("font-weight:600;" if cur == "en" else "")

    def set_now_playing(self, name: str) -> None:
        if name:
            self.now_playing.setText(f"{t('now_playing')}  ·  {name}")
        else:
            self.now_playing.setText("")

    def relayout(self) -> None:
        s = self.cfg
        self.brand.setStyleSheet(f"font-size:{scale_px(self, s, 12)}px; letter-spacing:6px;")
        self.title.setStyleSheet(f"font-size:{scale_px(self, s, 36)}px;")
        self.sub.setStyleSheet(f"font-size:{scale_px(self, s, 13)}px; letter-spacing:3px;")
        pad = scale_px(self, s, 14)
        width = scale_px(self, s, 280)
        for b in (self.btn_start, self.btn_train, self.btn_ops, self.btn_ac, self.btn_st, self.btn_ex):
            b.setFixedWidth(width)
            b.setStyleSheet(
                f"font-size:{scale_px(self, s, 15)}px; padding:{pad}px {pad + 8}px; text-align:center;"
            )
        self.status.setStyleSheet(f"font-size:{scale_px(self, s, 11)}px;")
        self.build.setStyleSheet(f"font-size:{scale_px(self, s, 11)}px;")
        self.drop_hint.setStyleSheet(f"font-size:{scale_px(self, s, 11)}px;")
        self.now_playing.setStyleSheet(f"font-size:{scale_px(self, s, 11)}px;")

    def set_health(self, cerber: str, vision: str, sim: str) -> None:
        ready = t("ready")
        down = t("down")
        c = ready if cerber in ("READY", ready) else down
        v = ready if vision in ("READY", ready) else down
        s = ready if sim in ("READY", ready) else down
        self.status.setText(
            f"CERBER     {c}        VISION     {v}        SIM        {s}"
        )
