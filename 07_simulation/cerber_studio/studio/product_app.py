"""CERBER Studio product shell — Main Menu / Aircraft / Mission / Settings / Flight."""

from __future__ import annotations

import logging
import sys
from enum import Enum, auto
from PySide6.QtCore import QEvent, Qt, QTimer, QUrl
from PySide6.QtGui import QDesktopServices, QGuiApplication, QKeyEvent
from PySide6.QtWidgets import QGridLayout, QStackedWidget, QWidget

from . import __version__
from .aircraft.registry import AircraftRegistry
from .audio.audio_manager import AudioManager
from .config.paths import log_dir
from .config.settings import UserSettings
from .display import apply_window_display, framebuffer_size, primary_screen, timer_interval_ms
from .missions.registry import MissionRegistry
from .overlay import draw_boxes
from .session import SimulationSession
from .ui.aircraft_select import AircraftSelectView
from .ui.error_view import ErrorView
from .ui.hud import ProductHud
from .ui.loading import LoadingView
from .ui.main_menu import MainMenuView
from .ui.mission_select import MissionSelectView
from .ui.overlay_host import OverlayHost
from .ui.pause_menu import PauseMenuView
from .ui.settings import SettingsView
from .ui.splash import SplashView
from .ui.theme import STYLESHEET
from .viewport import ViewportWidget

log = logging.getLogger("cerber_studio.product")


class AppState(Enum):
    BOOT = auto()
    MAIN_MENU = auto()
    AIRCRAFT_SELECT = auto()
    MISSION_SELECT = auto()
    SETTINGS = auto()
    LOADING = auto()
    SIMULATION = auto()
    PAUSED = auto()
    ERROR = auto()


class ProductWindow(QWidget):
    def __init__(self, settings: UserSettings) -> None:
        super().__init__()
        self.settings = settings
        self.setObjectName("ProductRoot")
        self.setWindowTitle("NULLXES CERBER Studio")
        self.setStyleSheet(STYLESHEET)
        self.setFocusPolicy(Qt.StrongFocus)
        self.state = AppState.BOOT
        self._settings_from = AppState.MAIN_MENU
        self._slot = "ego"
        self._load_gen = 0

        self.registry = AircraftRegistry()
        self.registry.scan()
        self.missions = MissionRegistry()
        self.missions.scan()

        ego = self.registry.get_or_first(settings.session.aircraft_id)
        tgt = self.registry.get(settings.session.target_id)
        if tgt is None:
            for item in self.registry.items:
                if item.id != ego.id:
                    tgt = item
                    break
        self.ego_id = ego.id
        self.target_id = tgt.id if tgt is not None else ego.id
        self.mission_id = settings.session.mission_id

        screen = primary_screen()
        rw, rh = framebuffer_size(screen.geometry().width(), screen.geometry().height(), settings)
        self.viewport = ViewportWidget(self, buffer_size=(rw, rh), settings=settings)
        self.session = SimulationSession(self.viewport, self.registry)
        self.viewport.set_frame_callback(self.session.on_frame, every=3)
        self.viewport.set_overlay_fn(self._product_boxes)
        self.audio = AudioManager()
        self.audio.apply(settings.audio)

        grid = QGridLayout(self)
        grid.setContentsMargins(0, 0, 0, 0)
        grid.setSpacing(0)
        grid.addWidget(self.viewport, 0, 0)

        self.hud = ProductHud(settings, self)
        grid.addWidget(self.hud, 0, 0)
        self.hud.hide()

        self.overlay = OverlayHost(self.viewport, self)
        grid.addWidget(self.overlay, 0, 0)
        ol = QGridLayout(self.overlay)
        ol.setContentsMargins(0, 0, 0, 0)
        self.stack = QStackedWidget(self.overlay)
        ol.addWidget(self.stack, 0, 0)

        self.splash = SplashView(settings)
        self.menu = MainMenuView(settings, __version__)
        self.ac_view = AircraftSelectView(settings)
        self.ms_view = MissionSelectView(settings)
        self.set_view = SettingsView(settings)
        self.load_view = LoadingView(settings)
        self.pause_view = PauseMenuView(settings)
        self.err_view = ErrorView(settings)
        self.pass_through = QWidget()
        self.pass_through.setAttribute(Qt.WA_TranslucentBackground, True)
        self.pass_through.setAttribute(Qt.WA_TransparentForMouseEvents, True)

        for w in (
            self.splash,
            self.menu,
            self.ac_view,
            self.ms_view,
            self.set_view,
            self.load_view,
            self.pause_view,
            self.err_view,
            self.pass_through,
        ):
            self.stack.addWidget(w)

        self.menu.start.connect(self._start_flight)
        self.menu.aircraft.connect(lambda: self._set_state(AppState.AIRCRAFT_SELECT))
        self.menu.mission.connect(lambda: self._set_state(AppState.MISSION_SELECT))
        self.menu.settings.connect(self._open_settings_from_menu)
        self.menu.exit_app.connect(self.close)
        self._wire_settings()
        self.ac_view.back.connect(lambda: self._set_state(AppState.MAIN_MENU))
        self.ac_view.prev_ac.connect(lambda: self._cycle_ac(-1))
        self.ac_view.next_ac.connect(lambda: self._cycle_ac(1))
        self.ac_view.select.connect(self._select_ac)
        self.ac_view.reset_view.connect(self.viewport.engine.reset_preview)
        self.ac_view.slot_ego.connect(lambda: self._set_slot("ego"))
        self.ac_view.slot_target.connect(lambda: self._set_slot("target"))
        self.ms_view.back.connect(lambda: self._set_state(AppState.MAIN_MENU))
        self.ms_view.selected.connect(self._start_flight)
        self.pause_view.resume.connect(lambda: self._set_state(AppState.SIMULATION))
        self.pause_view.restart.connect(self._restart_mission)
        self.pause_view.settings.connect(self._open_settings_from_pause)
        self.pause_view.aircraft.connect(self._pause_to_aircraft)
        self.pause_view.main_menu.connect(self._pause_to_menu)
        self.pause_view.exit_app.connect(self.close)
        self.err_view.fallback.connect(self._error_fallback)
        self.err_view.back.connect(self._error_back)

        self._ui_timer = QTimer(self)
        self._ui_timer.timeout.connect(self._tick)
        self._ui_timer.start(50)

        apply_window_display(self, settings)
        self._apply_runtime_settings()
        app = QGuiApplication.instance()
        if app is not None:
            app.installEventFilter(self)
        self._set_state(AppState.BOOT)
        QTimer.singleShot(900, lambda: self._set_state(AppState.MAIN_MENU))
        self._boot_preview()

    def _wire_settings(self) -> None:
        self.set_view.closed.connect(self._settings_closed)
        self.set_view.applied.connect(self._apply_runtime_settings)
        self.set_view.reset_settings.connect(self._reset_settings)
        self.set_view.reset_window.connect(self._reset_window)
        self.set_view.open_logs.connect(self._open_logs)

    def _boot_preview(self) -> None:
        self.viewport.engine.set_scene_mode("hangar")
        self.viewport.engine.input_enabled = False
        defn = self.registry.get_or_first(self.ego_id)
        err = self.session.apply_aircraft(defn)
        if err:
            log.warning("preview load: %s", err)
        tgt = self.registry.get(self.target_id)
        if tgt is not None:
            self.session.apply_target(tgt)

    def _page(self, widget: QWidget) -> None:
        self.stack.setCurrentWidget(widget)

    def _set_state(self, state: AppState) -> None:
        self.state = state
        eng = self.viewport.engine
        if state == AppState.BOOT:
            self._page(self.splash)
            self.splash.set_stage("SCANNING AIRCRAFT")
            self.hud.hide()
            eng.set_scene_mode("hangar")
            eng.input_enabled = False
            self.audio.scene = "hangar"
        elif state == AppState.MAIN_MENU:
            self._page(self.menu)
            self.hud.hide()
            eng.set_scene_mode("hangar")
            eng.input_enabled = False
            self.audio.scene = "hangar"
            self._refresh_menu_health()
            self._show_current_preview()
        elif state == AppState.AIRCRAFT_SELECT:
            self._page(self.ac_view)
            self.hud.hide()
            eng.set_scene_mode("hangar")
            eng.input_enabled = False
            self.audio.scene = "hangar"
            self._refresh_ac_view()
        elif state == AppState.MISSION_SELECT:
            self._page(self.ms_view)
            self.hud.hide()
            eng.set_scene_mode("hangar")
            self.ms_view.set_missions(self.missions.items, self.mission_id)
        elif state == AppState.SETTINGS:
            self._page(self.set_view)
            self.hud.hide()
            self._fill_system()
        elif state == AppState.LOADING:
            self._page(self.load_view)
            self.hud.hide()
            eng.input_enabled = False
        elif state == AppState.SIMULATION:
            self._page(self.pass_through)
            self.hud.show()
            eng.set_scene_mode("flight")
            eng.paused = False
            eng.input_enabled = True
            self.audio.scene = "flight"
            self.viewport.setFocus()
        elif state == AppState.PAUSED:
            self._page(self.pause_view)
            self.hud.show()
            eng.paused = True
            eng.input_enabled = False
        elif state == AppState.ERROR:
            self._page(self.err_view)
            self.hud.hide()
            eng.input_enabled = False

    def _refresh_menu_health(self) -> None:
        cerber = "READY" if self.session.vision_ready else "DOWN"
        vision = "READY" if self.session.vision_ready else "DOWN"
        sim = "READY"
        self.menu.set_health(cerber, vision, sim)

    def _show_current_preview(self) -> None:
        defn = self.registry.get_or_first(self.ego_id)
        if self.viewport.engine.definition is None or self.viewport.engine.definition.id != defn.id:
            self.session.apply_aircraft(defn)

    def _current_list(self):
        return self.registry.items

    def _set_slot(self, slot: str) -> None:
        self._slot = slot
        ident = self.ego_id if slot == "ego" else self.target_id
        defn = self.registry.get_or_first(ident)
        self.session.apply_aircraft(defn)
        self._refresh_ac_view()

    def _cycle_ac(self, delta: int) -> None:
        items = self._current_list()
        if not items:
            return
        ident = self.ego_id if self._slot == "ego" else self.target_id
        ids = [a.id for a in items]
        idx = ids.index(ident) if ident in ids else 0
        nxt = items[(idx + delta) % len(items)]
        if self._slot == "ego":
            self.ego_id = nxt.id
        else:
            self.target_id = nxt.id
        self.session.apply_aircraft(nxt)
        self.viewport.engine.reset_preview()
        self._refresh_ac_view()

    def _select_ac(self) -> None:
        self.settings.session.aircraft_id = self.ego_id
        self.settings.session.target_id = self.target_id
        self.settings.save()
        self._set_state(AppState.MISSION_SELECT)

    def _refresh_ac_view(self) -> None:
        ident = self.ego_id if self._slot == "ego" else self.target_id
        defn = self.registry.get_or_first(ident)
        ego = self.registry.get_or_first(self.ego_id)
        tgt = self.registry.get_or_first(self.target_id)
        self.ac_view.set_slot(self._slot, ego.name, tgt.name)
        self.ac_view.show_aircraft(defn)

    def _open_settings_from_menu(self) -> None:
        self._settings_from = AppState.MAIN_MENU
        self._set_state(AppState.SETTINGS)

    def _open_settings_from_pause(self) -> None:
        self._settings_from = AppState.PAUSED
        self._set_state(AppState.SETTINGS)

    def _settings_closed(self) -> None:
        self._set_state(self._settings_from)

    def _apply_runtime_settings(self) -> None:
        self.viewport.apply_settings(self.settings)
        refresh = float(self.screen().refreshRate() or 60.0) if self.screen() else 60.0
        self.viewport.set_timer_interval(timer_interval_ms(self.settings, refresh))
        w, h = framebuffer_size(self.width() or 1920, self.height() or 1080, self.settings)
        self.viewport.engine.resize_buffer(w, h)
        self.audio.apply(self.settings.audio)
        for view in (
            self.splash,
            self.menu,
            self.ac_view,
            self.ms_view,
            self.set_view,
            self.load_view,
            self.pause_view,
            self.hud,
        ):
            if hasattr(view, "relayout"):
                view.relayout()
        apply_window_display(self, self.settings)

    def _reset_settings(self) -> None:
        from .config.paths import settings_path
        from .config.settings import UserSettings as US

        fresh = US()
        self.settings.display = fresh.display
        self.settings.graphics = fresh.graphics
        self.settings.audio = fresh.audio
        self.settings.hud = fresh.hud
        self.settings.controls = fresh.controls
        self.settings.simulation = fresh.simulation
        self.settings.save(settings_path())
        idx = self.stack.indexOf(self.set_view)
        self.stack.removeWidget(self.set_view)
        self.set_view.deleteLater()
        self.set_view = SettingsView(self.settings)
        self.stack.insertWidget(idx, self.set_view)
        self._wire_settings()
        self.stack.setCurrentWidget(self.set_view)
        self._apply_runtime_settings()
        self._fill_system()

    def _reset_window(self) -> None:
        self.settings.display.mode = "borderless"
        self.settings.save()
        apply_window_display(self, self.settings)

    def _open_logs(self) -> None:
        QDesktopServices.openUrl(QUrl.fromLocalFile(str(log_dir())))

    def _fill_system(self) -> None:
        ort = "unavailable"
        gpu = "—"
        try:
            import onnxruntime as ortmod

            providers = list(ortmod.get_available_providers())
            ort = ", ".join(providers) if providers else "none"
            gpu = "CUDA" if "CUDAExecutionProvider" in providers else "CPU"
        except Exception:  # noqa: BLE001
            pass
        sc = self.screen() or QGuiApplication.primaryScreen()
        g = sc.geometry()
        ac = self.registry.get_or_first(self.ego_id)
        self.set_view.set_system_info(
            {
                "cerber": "UP" if self.session.worker_alive else "DOWN",
                "ort": ort,
                "gpu": gpu,
                "display": f"{g.width()}×{g.height()}",
                "fps": f"{self.viewport.engine.render_fps:.0f}",
                "model": ac.name,
                "build": __version__,
            }
        )

    def _start_flight(self) -> None:
        picked = self.ms_view.current()
        if picked is not None:
            self.mission_id = picked.id
        self.settings.session.aircraft_id = self.ego_id
        self.settings.session.target_id = self.target_id
        self.settings.session.mission_id = self.mission_id
        self.settings.save()
        self._set_state(AppState.LOADING)
        self._load_gen += 1
        gen = self._load_gen
        QTimer.singleShot(0, lambda: self._load_stage_aircraft(gen))

    def _load_stage_aircraft(self, gen: int) -> None:
        if gen != self._load_gen:
            return
        self.load_view.set_stage("AIRCRAFT", "Loading visual model")
        defn = self.registry.get_or_first(self.ego_id)
        err = self.session.apply_aircraft(defn)
        if err:
            self.err_view.show_error(
                "AIRCRAFT MODEL FAILED TO LOAD",
                f"{err}\n\nTraceback written to the log directory.",
                fallback=True,
            )
            self._set_state(AppState.ERROR)
            return
        QTimer.singleShot(0, lambda: self._load_stage_world(gen))

    def _load_stage_world(self, gen: int) -> None:
        if gen != self._load_gen:
            return
        self.load_view.set_stage("WORLD", "Building flight environment")
        tgt = self.registry.get(self.target_id)
        terr = self.session.apply_target(tgt)
        if terr:
            log.warning("target model failed: %s — procedural fallback in use", terr)
        QTimer.singleShot(0, lambda: self._load_stage_vision(gen))

    def _load_stage_vision(self, gen: int) -> None:
        if gen != self._load_gen:
            return
        self.load_view.set_stage("VISION", "Starting CERBER worker")
        detail = self.session.start_worker()
        log.info("vision: %s", detail)
        QTimer.singleShot(200, lambda: self._load_stage_mission(gen))

    def _load_stage_mission(self, gen: int) -> None:
        if gen != self._load_gen:
            return
        self.load_view.set_stage("MISSION", "Applying demo mission")
        mission = self.missions.get_or_first(self.mission_id)
        self.session.apply_mission(mission)
        self.session.start_world()
        self._set_state(AppState.SIMULATION)

    def _restart_mission(self) -> None:
        self.session.restart()
        self._set_state(AppState.SIMULATION)

    def _pause_to_menu(self) -> None:
        self.session.teardown()
        self._set_state(AppState.MAIN_MENU)

    def _pause_to_aircraft(self) -> None:
        self.session.teardown()
        self._set_state(AppState.AIRCRAFT_SELECT)

    def _error_fallback(self) -> None:
        from .aircraft.registry import builtin_from_preset

        defn = builtin_from_preset("ar_wing")
        self.ego_id = defn.id
        self.session.apply_aircraft(defn)
        self._set_state(AppState.AIRCRAFT_SELECT)

    def _error_back(self) -> None:
        self.session.teardown()
        self._set_state(AppState.AIRCRAFT_SELECT)

    def _product_boxes(self, rgb):
        if self.state not in (AppState.SIMULATION, AppState.PAUSED):
            return rgb
        hud = self.settings.hud
        if not hud.hud or not hud.target_boxes:
            return rgb
        if self.viewport.engine.camera_mode != "nose":
            return rgb
        if not self.session.last_detections:
            return rgb
        bgr = rgb[:, :, ::-1].copy()
        return draw_boxes(bgr, self.session.last_detections)[:, :, ::-1].copy()

    def _tick(self) -> None:
        eng = self.viewport.engine
        st = eng.dynamics.state
        self.session.poll_results()
        self.audio.throttle = st.throttle
        self.audio.airspeed = st.speed
        self.audio.max_speed = eng.params.max_speed
        if self.state in (AppState.SIMULATION, AppState.PAUSED):
            mission = self.session.mission
            tgt = self.session.target
            self.hud.update_hud(
                mode=eng.flight_mode,
                alt=st.z,
                spd=st.speed,
                thr=st.throttle,
                cerber_ok=self.session.health.vision_ok if self.session.worker_alive else None,
                cerber_detail=self.session.health.detail,
                fps=eng.render_fps,
                target_name=tgt.name if tgt is not None and eng.target_visible else "",
                target_dist=eng.target_distance() if eng.target_visible else None,
                track_id=self.session.last_track_id,
                mission_name=mission.name if mission is not None else "",
                debug=self.session.health.detail if self.settings.hud.debug_labels else "",
            )
        if self.state == AppState.MAIN_MENU:
            self._refresh_menu_health()
        if self.state == AppState.SETTINGS:
            self.set_view.sys_fps.setText(f"{eng.render_fps:.0f}")

    def eventFilter(self, watched, event) -> bool:
        if event.type() == QEvent.KeyPress:
            key = event.key()
            if key == Qt.Key_Escape:
                self.keyPressEvent(event)
                return True
            if self.state == AppState.SIMULATION and key in (
                Qt.Key_Space,
                Qt.Key_R,
                Qt.Key_C,
                Qt.Key_F1,
                Qt.Key_1,
                Qt.Key_2,
                Qt.Key_3,
                Qt.Key_4,
            ):
                self.keyPressEvent(event)
                return True
        if event.type() == QEvent.KeyRelease and self.state == AppState.SIMULATION:
            self.keyReleaseEvent(event)
            return event.key() in (
                Qt.Key_W,
                Qt.Key_S,
                Qt.Key_A,
                Qt.Key_D,
                Qt.Key_Q,
                Qt.Key_E,
                Qt.Key_Shift,
                Qt.Key_Control,
            )
        return super().eventFilter(watched, event)

    def keyPressEvent(self, event: QKeyEvent) -> None:
        key = event.key()
        if key == Qt.Key_Escape:
            if self.state == AppState.SIMULATION:
                self._set_state(AppState.PAUSED)
                return
            if self.state == AppState.PAUSED:
                self._set_state(AppState.SIMULATION)
                return
            if self.state in (AppState.AIRCRAFT_SELECT, AppState.MISSION_SELECT, AppState.SETTINGS):
                if self.state == AppState.SETTINGS:
                    self.set_view._on_back()
                    return
                self._set_state(AppState.MAIN_MENU)
                return
        if self.state == AppState.SIMULATION:
            if key == Qt.Key_Space:
                self.viewport.engine.launch()
                return
            if key == Qt.Key_R:
                self.viewport.engine.reset_ego()
                return
            if key == Qt.Key_F1:
                self.viewport.engine.reset_target()
                return
            if key == Qt.Key_C:
                eng = self.viewport.engine
                eng.camera_mode = "chase" if eng.camera_mode == "nose" else "nose"
                return
            if key == Qt.Key_1:
                self.viewport.engine.flight_mode = "MANUAL"
            elif key == Qt.Key_2:
                self.viewport.engine.flight_mode = "ASSIST"
            elif key == Qt.Key_3:
                self.viewport.engine.flight_mode = "PURSUIT"
            elif key == Qt.Key_4:
                self.viewport.engine.flight_mode = "MISSION"
            self.viewport.keyPressEvent(event)
            return
        super().keyPressEvent(event)

    def keyReleaseEvent(self, event: QKeyEvent) -> None:
        if self.state == AppState.SIMULATION:
            self.viewport.keyReleaseEvent(event)
            return
        super().keyReleaseEvent(event)

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        if self.state != AppState.BOOT:
            w, h = framebuffer_size(self.width(), self.height(), self.settings)
            self.viewport.engine.resize_buffer(w, h)
            for view in (self.menu, self.ac_view, self.ms_view, self.set_view, self.hud, self.pause_view):
                if hasattr(view, "relayout"):
                    view.relayout()

    def closeEvent(self, event) -> None:
        self.settings.session.aircraft_id = self.ego_id
        self.settings.session.target_id = self.target_id
        self.settings.session.mission_id = self.mission_id
        self.settings.save()
        self.session.teardown()
        self.audio.stop()
        app = QGuiApplication.instance()
        if app is not None:
            app.removeEventFilter(self)
        try:
            self.viewport.engine.close_engine()
        except Exception:  # noqa: BLE001
            pass
        super().closeEvent(event)


def configure_product_logging() -> Path:
    path = log_dir() / "studio.log"
    logging.basicConfig(
        filename=str(path),
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
        force=True,
    )
    return path
