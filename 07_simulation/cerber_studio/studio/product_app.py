"""CERBER Studio product shell — Main Menu / Aircraft / Mission / Settings / Flight."""

from __future__ import annotations

import logging
import sys
from pathlib import Path
from enum import Enum, auto
from PySide6.QtCore import QEvent, Qt, QTimer, QUrl
from PySide6.QtGui import QDesktopServices, QGuiApplication, QKeyEvent
from PySide6.QtWidgets import QGridLayout, QStackedWidget, QWidget

from . import __version__
from .aircraft.registry import AircraftRegistry
from .audio.audio_manager import AudioManager
from .audio.playlist import import_tracks
from .config.paths import log_dir
from .config.settings import UserSettings
from .display import apply_window_display, framebuffer_size, primary_screen, timer_interval_ms
from .i18n import set_lang, t
from .missions.registry import MissionRegistry
from .overlay import draw_boxes
from .session import SimulationSession
from .ui.aircraft_select import AircraftSelectView
from .ui.aviation_map import AviationMap
from .ui.cinematic import CinematicView
from .ui.end_card import EndCardView
from .ui.error_view import ErrorView
from .ui.hud import ProductHud, compass_tape
from .ui.loading import LoadingView
from .ui.main_menu import MainMenuView
from .ui.mission_select import MissionSelectView
from .ui.now_playing import NowPlayingBar
from .ui.overlay_host import OverlayHost
from .ui.pause_menu import PauseMenuView
from .ui.pilot_record import PilotRecordView
from .ui.region_select import RegionSelectView
from .ui.replay_timeline import ReplayTimeline
from .ui.settings import SettingsView
from .ui.splash import SplashView
from .ui.theme import STYLESHEET
from .viewport import ViewportWidget
from .world_gen.world_profile import list_profiles

log = logging.getLogger("cerber_studio.product")


class AppState(Enum):
    BOOT = auto()
    MAIN_MENU = auto()
    AIRCRAFT_SELECT = auto()
    REGION_SELECT = auto()
    MISSION_SELECT = auto()
    SETTINGS = auto()
    LOADING = auto()
    SIMULATION = auto()
    PAUSED = auto()
    CINEMATIC = auto()
    END_CARD = auto()
    PILOT = auto()
    ERROR = auto()


class ProductWindow(QWidget):
    def __init__(self, settings: UserSettings) -> None:
        super().__init__()
        self.settings = settings
        set_lang(settings.language)
        self.setObjectName("ProductRoot")
        self.setWindowTitle("NULLXES BLACKBOX")
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
        self.now_bar = NowPlayingBar(settings, self)
        grid.addWidget(self.now_bar, 0, 0, 1, 1, Qt.AlignBottom)
        self.now_bar.hide()

        self.map_view = AviationMap(settings, self)
        grid.addWidget(self.map_view, 0, 0)
        self.map_view.hide()
        self.timeline = ReplayTimeline(settings, self)
        self.timeline.setMaximumHeight(240)
        grid.addWidget(self.timeline, 0, 0, 1, 1, Qt.AlignBottom)
        self.timeline.hide()

        self.overlay = OverlayHost(self.viewport, self)
        grid.addWidget(self.overlay, 0, 0)
        ol = QGridLayout(self.overlay)
        ol.setContentsMargins(0, 0, 0, 0)
        self.stack = QStackedWidget(self.overlay)
        ol.addWidget(self.stack, 0, 0)

        self.splash = SplashView(settings)
        self.menu = MainMenuView(settings, __version__)
        self.ac_view = AircraftSelectView(settings)
        self.region_view = RegionSelectView(settings)
        self.ms_view = MissionSelectView(settings)
        self.set_view = SettingsView(settings)
        self.load_view = LoadingView(settings)
        self.pause_view = PauseMenuView(settings)
        self.end_view = EndCardView(settings)
        self.pilot_view = PilotRecordView(settings)
        self.err_view = ErrorView(settings)
        self.cine_view = CinematicView(settings)
        self.pass_through = QWidget()
        self.pass_through.setAttribute(Qt.WA_TranslucentBackground, True)
        self.pass_through.setAttribute(Qt.WA_TransparentForMouseEvents, True)

        for w in (
            self.splash,
            self.menu,
            self.ac_view,
            self.region_view,
            self.ms_view,
            self.set_view,
            self.load_view,
            self.pause_view,
            self.end_view,
            self.pilot_view,
            self.err_view,
            self.cine_view,
            self.pass_through,
        ):
            self.stack.addWidget(w)

        self.menu.free_flight.connect(self._free_flight_flow)
        self.menu.training.connect(lambda: self._start_named("flight_training"))
        self.menu.aircraft.connect(lambda: self._set_state(AppState.AIRCRAFT_SELECT))
        self.menu.mission.connect(lambda: self._set_state(AppState.MISSION_SELECT))
        self.menu.settings.connect(self._open_settings_from_menu)
        self.menu.exit_app.connect(self.close)
        self.menu.language.connect(self._set_language)
        self.menu.tracks_dropped.connect(self._import_tracks)
        self._wire_settings()
        self.ac_view.back.connect(lambda: self._set_state(AppState.MAIN_MENU))
        self.ac_view.prev_ac.connect(lambda: self._cycle_ac(-1))
        self.ac_view.next_ac.connect(lambda: self._cycle_ac(1))
        self.ac_view.select.connect(self._hangar_fly)
        self.ac_view.reset_view.connect(self.viewport.engine.reset_preview)
        self.ac_view.slot_ego.connect(lambda: self._set_slot("ego"))
        self.ac_view.slot_target.connect(lambda: self._set_slot("target"))
        self.region_view.back.connect(lambda: self._set_state(AppState.AIRCRAFT_SELECT))
        self.region_view.selected.connect(self._region_fly)
        self.region_view.preview.connect(self._preview_region)
        self.ms_view.back.connect(lambda: self._set_state(AppState.MAIN_MENU))
        self.ms_view.selected.connect(self._start_flight)
        self.pause_view.resume.connect(lambda: self._set_state(AppState.SIMULATION))
        self.pause_view.restart.connect(self._restart_mission)
        self.pause_view.settings.connect(self._open_settings_from_pause)
        self.pause_view.aircraft.connect(self._pause_to_aircraft)
        self.pause_view.main_menu.connect(self._pause_to_menu)
        self.pause_view.exit_app.connect(self.close)
        self.end_view.replay.connect(self._start_replay)
        self.end_view.flight_path.connect(lambda: self._replay_cam("orbit"))
        self.end_view.events.connect(lambda: self._replay_cam("ground"))
        self.end_view.cerber.connect(self._end_operator)
        self.end_view.statistics.connect(lambda: self._set_state(AppState.PILOT))
        self.end_view.hangar.connect(self._pause_to_aircraft)
        self.pilot_view.back.connect(lambda: self._set_state(AppState.MAIN_MENU))
        self.now_bar.prev_track.connect(self.audio.prev_track)
        self.now_bar.next_track.connect(self.audio.next_track)
        self.now_bar.play_pause.connect(self.audio.toggle_music)
        self.now_bar.seek.connect(self.audio.seek_frac)
        self.now_bar.shuffle.connect(self.audio.toggle_shuffle)
        self.err_view.fallback.connect(self._error_fallback)
        self.err_view.back.connect(self._error_back)
        self.cine_view.closed.connect(self._exit_cinematic)
        self.cine_view.screenshot.connect(self._cinematic_shot)
        self.cine_view.fov.connect(self._cinematic_fov)
        self.cine_view.tod.connect(self._cinematic_tod)
        self.cine_view.reset_tod.connect(self._cinematic_reset_tod)
        self.timeline.seek.connect(self.viewport.engine.seek_replay)
        self.timeline.close.connect(self.timeline.hide)

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
        self.set_view.language.connect(self._set_language)
        self.set_view.tracks_dropped.connect(self._import_tracks)
        self.set_view.live_audio.connect(self._live_audio)
        self.set_view.play_slot.connect(self._play_audio_slot)

    def _live_audio(self) -> None:
        self.audio.apply(self.settings.audio)

    def _play_audio_slot(self, index: int) -> None:
        self.audio.apply(self.settings.audio)
        self.audio.play_slot(index)

    def _set_language(self, code: str) -> None:
        chosen = set_lang(code)
        self.settings.language = chosen
        self.settings.save()
        self._retranslate_all()

    def _import_tracks(self, paths: list) -> None:
        import_tracks([Path(p) for p in paths])
        self.audio.reload_playlist()
        self.set_view.refresh_playlist()
        name = self.audio.current_track_name()
        self.menu.set_now_playing(name)

    def _retranslate_all(self) -> None:
        for view in (
            self.splash,
            self.menu,
            self.ac_view,
            self.region_view,
            self.ms_view,
            self.set_view,
            self.load_view,
            self.pause_view,
            self.end_view,
            self.pilot_view,
            self.err_view,
            self.cine_view,
        ):
            if hasattr(view, "retranslate"):
                view.retranslate()
        self._refresh_menu_health()
        if self.state == AppState.BOOT:
            self.splash.set_stage("scanning_aircraft")
        if self.state == AppState.AIRCRAFT_SELECT:
            self._refresh_ac_view()
        if self.state == AppState.MISSION_SELECT:
            self.ms_view.set_missions(self.missions.items, self.mission_id)
        name = self.audio.current_track_name()
        self.menu.set_now_playing(name)

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
        if state not in (AppState.SIMULATION, AppState.PAUSED, AppState.CINEMATIC, AppState.END_CARD):
            self.map_view.hide()
            self.timeline.hide()
        if state == AppState.BOOT:
            self._page(self.splash)
            self.splash.set_stage("scanning_aircraft")
            self.hud.hide()
            eng.set_scene_mode("hangar")
            eng.input_enabled = False
            self.overlay.set_forward_empty(False)
            self.audio.set_scene("menu")
        elif state == AppState.MAIN_MENU:
            self._page(self.menu)
            self.hud.hide()
            self.now_bar.hide()
            eng.set_scene_mode("hangar")
            eng.input_enabled = False
            self.overlay.set_forward_empty(False)
            self.audio.set_scene("menu")
            self._refresh_menu_health()
            self._show_current_preview()
        elif state == AppState.AIRCRAFT_SELECT:
            self._page(self.ac_view)
            self.hud.hide()
            self.now_bar.hide()
            eng.set_scene_mode("hangar")
            eng.input_enabled = False
            self.overlay.set_forward_empty(True)
            self.audio.set_scene("hangar")
            eng.rebuild_hangar_line(self.registry.items)
            ids = [a.id for a in self.registry.items]
            eng.hangar_index = ids.index(self.ego_id) if self.ego_id in ids else 0
            self._refresh_ac_view()
        elif state == AppState.REGION_SELECT:
            self._page(self.region_view)
            self.hud.hide()
            self.now_bar.hide()
            eng.input_enabled = False
            self.overlay.set_forward_empty(True)
            self.audio.set_scene("menu")
            self.region_view.set_profiles(list_profiles(), self.settings.session.region_id)
        elif state == AppState.MISSION_SELECT:
            self._page(self.ms_view)
            self.hud.hide()
            self.now_bar.hide()
            eng.set_scene_mode("hangar")
            self.overlay.set_forward_empty(False)
            self.audio.set_scene("menu")
            items = list(self.missions.items)
            if not self.session.pilot.night_unlocked:
                items = [m for m in items if m.clearance != "night"]
            self.ms_view.set_missions(items, self.mission_id)
        elif state == AppState.END_CARD:
            self._page(self.end_view)
            self.hud.show()
            self.now_bar.show()
            eng.paused = True
            eng.input_enabled = False
            self.overlay.set_forward_empty(False)
            self.audio.set_scene("paused")
        elif state == AppState.PILOT:
            self._page(self.pilot_view)
            self.hud.hide()
            self.now_bar.hide()
            self.pilot_view.show_record(self.session.pilot)
            self.overlay.set_forward_empty(False)
            self.audio.set_scene("menu")
        elif state == AppState.SETTINGS:
            self._page(self.set_view)
            self.hud.hide()
            self.overlay.set_forward_empty(False)
            if self._settings_from == AppState.PAUSED:
                self.audio.set_scene("paused")
            else:
                self.audio.set_scene("menu")
            self._fill_system()
        elif state == AppState.LOADING:
            self._page(self.load_view)
            self.hud.hide()
            self.now_bar.hide()
            eng.input_enabled = False
            self.overlay.set_forward_empty(False)
            self.audio.set_scene("loading")
        elif state == AppState.SIMULATION:
            self._page(self.pass_through)
            self.hud.show()
            self.now_bar.show()
            was_cine = eng.cinematic
            eng.set_scene_mode("flight")
            eng.paused = False
            eng.input_enabled = True
            if was_cine:
                eng.exit_cinematic()
            self.overlay.set_forward_empty(True)
            self.audio.set_scene("flight")
            self.viewport.setFocus()
        elif state == AppState.CINEMATIC:
            self._page(self.cine_view)
            self.hud.hide()
            self.now_bar.hide()
            self.map_view.hide()
            eng.enter_cinematic()
            self.overlay.set_forward_empty(True)
            self.audio.set_scene("paused")
            self.viewport.setFocus()
        elif state == AppState.PAUSED:
            self._page(self.pause_view)
            self.hud.show()
            eng.paused = True
            eng.input_enabled = False
            self.overlay.set_forward_empty(False)
            self.audio.set_scene("paused")
        elif state == AppState.ERROR:
            self._page(self.err_view)
            self.hud.hide()
            eng.input_enabled = False
            self.overlay.set_forward_empty(False)
            self.audio.set_scene("menu")

    def _refresh_menu_health(self) -> None:
        self.menu.set_health(
            t("ready") if self.session.vision_ready else t("down"),
            t("ready") if self.session.vision_ready else t("down"),
            t("ready"),
        )

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
        ids = [a.id for a in items]
        self.viewport.engine.hangar_index = ids.index(nxt.id) if nxt.id in ids else 0
        self.viewport.engine.reset_preview()
        self._refresh_ac_view()

    def _hangar_fly(self) -> None:
        self.settings.session.aircraft_id = self.ego_id
        self.settings.session.target_id = self.target_id
        self.settings.save()
        self.mission_id = "free_flight"
        self._set_state(AppState.REGION_SELECT)

    def _select_ac(self) -> None:
        self._hangar_fly()

    def _free_flight_flow(self) -> None:
        self.mission_id = "free_flight"
        self._set_state(AppState.REGION_SELECT)

    def _preview_region(self, region_id: str) -> None:
        self.viewport.engine.preview_region(region_id)

    def _region_fly(self, region_id: str) -> None:
        self.settings.session.region_id = region_id
        self.settings.save()
        self.mission_id = "free_flight"
        self._start_flight()

    def _start_replay(self) -> None:
        folder = self.session.flight_dir
        if folder is None:
            return
        self._set_state(AppState.SIMULATION)
        self.viewport.engine.start_replay(folder)
        self.viewport.engine.camera_mode = "flyby"
        self.timeline.set_data(self.viewport.engine.replay_poses, self.viewport.engine.replay_events)
        self.timeline.show()

    def _replay_cam(self, mode: str) -> None:
        folder = self.session.flight_dir
        if folder is None:
            return
        self._set_state(AppState.SIMULATION)
        self.viewport.engine.start_replay(folder)
        self.viewport.engine.camera_mode = mode
        self.timeline.set_data(self.viewport.engine.replay_poses, self.viewport.engine.replay_events)
        self.timeline.show()

    def _replay_cam(self, mode: str) -> None:
        folder = self.session.flight_dir
        if folder is None:
            return
        self._set_state(AppState.SIMULATION)
        self.viewport.engine.start_replay(folder)
        self.viewport.engine.camera_mode = mode

    def _end_operator(self) -> None:
        self.settings.hud.operator_tab = True
        self._replay_cam("nose")

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
        scene = {
            AppState.BOOT: "menu",
            AppState.MAIN_MENU: "menu",
            AppState.AIRCRAFT_SELECT: "hangar",
            AppState.REGION_SELECT: "menu",
            AppState.MISSION_SELECT: "menu",
            AppState.SETTINGS: "menu",
            AppState.LOADING: "loading",
            AppState.SIMULATION: "flight",
            AppState.CINEMATIC: "paused",
            AppState.PAUSED: "paused",
            AppState.END_CARD: "paused",
            AppState.PILOT: "menu",
            AppState.ERROR: "menu",
        }.get(self.state, "menu")
        self.audio.set_scene(scene)
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
        self.settings.language = fresh.language
        self.settings.display = fresh.display
        self.settings.graphics = fresh.graphics
        self.settings.audio = fresh.audio
        self.settings.hud = fresh.hud
        self.settings.controls = fresh.controls
        self.settings.simulation = fresh.simulation
        set_lang(self.settings.language)
        self.settings.save(settings_path())
        idx = self.stack.indexOf(self.set_view)
        self.stack.removeWidget(self.set_view)
        self.set_view.deleteLater()
        self.set_view = SettingsView(self.settings)
        self.stack.insertWidget(idx, self.set_view)
        self._wire_settings()
        self.stack.setCurrentWidget(self.set_view)
        self._retranslate_all()
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

    def _start_named(self, mission_id: str) -> None:
        self.mission_id = mission_id
        self._start_flight()

    def _start_flight(self) -> None:
        if self.state == AppState.MISSION_SELECT:
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
        self.load_view.set_stage("aircraft", "load_visual")
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
        self.load_view.set_stage("world", "load_world")
        tgt = self.registry.get(self.target_id)
        terr = self.session.apply_target(tgt)
        if terr:
            log.warning("target model failed: %s — procedural fallback in use", terr)
        QTimer.singleShot(0, lambda: self._load_stage_vision(gen))

    def _load_stage_vision(self, gen: int) -> None:
        if gen != self._load_gen:
            return
        self.load_view.set_stage("vision", "load_vision")
        detail = self.session.start_worker()
        log.info("vision: %s", detail)
        QTimer.singleShot(200, lambda: self._load_stage_mission(gen))

    def _load_stage_mission(self, gen: int) -> None:
        if gen != self._load_gen:
            return
        self.load_view.set_stage("mission", "load_mission")
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
        items = [a for a in self.registry.items if a.visual.path is not None]
        if not items:
            self._set_state(AppState.AIRCRAFT_SELECT)
            return
        defn = items[0]
        self.ego_id = defn.id
        self.session.apply_aircraft(defn)
        self._set_state(AppState.AIRCRAFT_SELECT)

    def _error_back(self) -> None:
        self.session.teardown()
        self._set_state(AppState.AIRCRAFT_SELECT)

    def _product_boxes(self, rgb):
        if self.state not in (AppState.SIMULATION, AppState.PAUSED, AppState.END_CARD):
            return rgb
        hud = self.settings.hud
        if not hud.hud or not hud.target_boxes:
            return rgb
        eng = self.viewport.engine
        operator = (eng.hud_layer == "operator") or hud.operator_tab or eng.operator_tab
        if eng.camera_mode != "nose" and not operator:
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
        self.audio.camera_mode = eng.camera_mode
        cam = eng.camera.getPos()
        self.audio._pan = float(max(-0.85, min(0.85, (st.x - cam.getX()) * 0.015)))
        self.audio.rain_level = eng.world.atmosphere.rain
        self.audio.storm_level = eng.world.atmosphere.storm
        tod = eng.world.atmosphere.time_of_day_h
        tod_key = "night" if tod >= 21 or tod < 5 else "sunset" if tod >= 17.5 else "clear"
        intensity = "pursuit" if eng.flight_mode in ("PURSUIT", "FOLLOW") else "cruise"
        self.audio.mix_ctx = {
            "region": self.settings.session.region_id,
            "weather": eng.world.atmosphere.preset,
            "tod": tod_key,
            "intensity": intensity,
            "mission": self.mission_id,
        }
        if self.state == AppState.SIMULATION and not eng.paused and not eng.replay_active:
            self.session.tick_ops(0.05)
            self.session.tick_discovery()
        if self.state == AppState.SIMULATION and eng.blackbox.active and not eng.replay_active:
            sample = eng.record_sample()
            sample["music"] = self.audio.current_track_name()
            sample["cerber"] = [
                {"id": int(t.track_id), "name": str(getattr(t, "name", ""))} for t in self.session.last_tracks
            ]
            if eng.blackbox.tick(0.05, sample):
                eng.runtime.recorder_writes += 1
            eng.runtime.recorder_expected = int(st.flight_time * 20)
            if st.phase.value in ("STOPPED", "CRASHED") and (st.landing_grade or st.phase.value == "CRASHED"):
                self.session.finish_flight()
                mission = self.session.mission
                cert = self.session.director.grade if mission is not None and mission.challenge else None
                self.end_view.set_summary(
                    st.flight_time,
                    st.distance_m / 1000.0,
                    st.max_alt,
                    st.max_speed,
                    st.landing_grade,
                    cert=cert,
                    op_name=mission.name if mission is not None else "",
                )
                self._set_state(AppState.END_CARD)
        if self.state in (AppState.SIMULATION, AppState.PAUSED, AppState.END_CARD, AppState.CINEMATIC):
            mission = self.session.mission
            tgt = self.session.target
            layer = eng.hud_layer
            clock_h = eng.world.atmosphere.clock_h
            clock = f"{int(clock_h) % 24:02d}:{int((clock_h % 1.0) * 60):02d}"
            wind = f"WIND {eng.world.atmosphere.wind_mps:.0f}"
            af = eng.world.graph.airfields[0] if eng.world.graph.airfields else None
            home = None
            if af is not None:
                home = float(( (st.x - af.x) ** 2 + (st.y - af.y) ** 2 ) ** 0.5)
            dist = eng.target_distance() if eng.target_visible and layer == "operator" else home
            op_label = self.session.director.label() if mission is not None else ""
            self.hud.update_hud(
                mode=eng.flight_mode,
                alt=st.agl,
                spd=st.speed,
                thr=st.throttle,
                cerber_ok=self.session.health.vision_ok if self.session.worker_alive else None,
                cerber_detail=self.session.health.detail,
                fps=eng.render_fps,
                target_name=tgt.name if tgt is not None and eng.target_visible else "",
                target_dist=eng.target_distance() if eng.target_visible else None,
                track_id=self.session.last_track_id,
                mission_name=op_label or (mission.name if mission is not None else ""),
                debug=self.session.health.detail if self.settings.hud.debug_labels else "",
                phase=st.phase.value if hasattr(st.phase, "value") else str(st.phase),
                cue=eng.replay_warning or self._launch_cue(eng),
                training=eng.training.label(),
                hint=t(eng.training.hint_key()) if eng.training.active else "",
                hdg=st.yaw_deg,
                vs=float(st.vz),
                dist=dist,
                wind=wind,
                clock=clock,
                layer=layer,
                compass=compass_tape(st.yaw_deg),
            )
            if self.state == AppState.CINEMATIC or layer == "clean":
                self.now_bar.hide()
            else:
                self.now_bar.set_track(self.audio.current_track_name(), self.audio._music_paused, self.audio.music_frac())
                self.now_bar.show()
            if self.map_view.isVisible():
                cerber_xy = None
                if self.session.last_track_id is not None and eng.target_visible:
                    tp = eng.target.getPos()
                    cerber_xy = (float(tp.getX()), float(tp.getY()))
                self.map_view.set_world(
                    eng.world.graph,
                    (st.x, st.y, st.z),
                    eng._trail,
                    list(self.session.pilot.discovered),
                    cerber_xy,
                )
            if self.timeline.isVisible() and eng.replay_active:
                self.timeline.set_index(eng.replay_i)
        if self.state == AppState.MAIN_MENU:
            self._refresh_menu_health()
            self.menu.set_now_playing(self.audio.current_track_name())
        if self.state == AppState.SETTINGS:
            self.set_view.sys_fps.setText(f"{eng.render_fps:.0f}")

    def _launch_cue(self, eng) -> str:
        raw = eng.dynamics.launch_cue()
        if raw == "THROTTLE UP TO LAUNCH":
            return t("throttle_up_launch")
        if raw == "READY FOR LAUNCH":
            return f"{t('ready_launch')}     {t('press_launch')}"
        if raw == "FLIGHT COMPLETE":
            return t("flight_complete")
        return raw

    def _toggle_map(self) -> None:
        if self.state not in (AppState.SIMULATION, AppState.PAUSED):
            return
        if self.map_view.isVisible():
            self.map_view.hide()
            return
        self.map_view.show()
        self.map_view.raise_()

    def _exit_cinematic(self) -> None:
        self._set_state(AppState.SIMULATION)

    def _cinematic_fov(self, value: int) -> None:
        eng = self.viewport.engine
        eng.camLens.setFov(float(value))
        eng._fov = float(value)

    def _cinematic_tod(self, clock_h: float) -> None:
        eng = self.viewport.engine
        eng.world.atmosphere.set_visual_clock(clock_h)
        eng._apply_sky(rebuild=True)

    def _cinematic_reset_tod(self) -> None:
        eng = self.viewport.engine
        eng.world.atmosphere.set_visual_clock(None)
        eng._apply_sky(rebuild=True)

    def _cinematic_shot(self) -> None:
        self.viewport.engine.screenshot()

    def eventFilter(self, watched, event) -> bool:
        if event.type() == QEvent.KeyPress:
            key = event.key()
            if key == Qt.Key_Escape:
                self.keyPressEvent(event)
                return True
            if self.state == AppState.SIMULATION and key in (
                Qt.Key_Space,
                Qt.Key_E,
                Qt.Key_X,
                Qt.Key_R,
                Qt.Key_C,
                Qt.Key_Tab,
                Qt.Key_F1,
                Qt.Key_1,
                Qt.Key_2,
                Qt.Key_3,
                Qt.Key_4,
                Qt.Key_M,
                Qt.Key_P,
                Qt.Key_H,
            ):
                self.keyPressEvent(event)
                return True
            if self.state == AppState.CINEMATIC and key in (Qt.Key_P, Qt.Key_C):
                self.keyPressEvent(event)
                return True
        if event.type() == QEvent.KeyRelease and self.state in (AppState.SIMULATION, AppState.CINEMATIC):
            self.keyReleaseEvent(event)
            return event.key() in (
                Qt.Key_W,
                Qt.Key_S,
                Qt.Key_A,
                Qt.Key_D,
                Qt.Key_Q,
                Qt.Key_E,
                Qt.Key_X,
                Qt.Key_Shift,
                Qt.Key_Control,
            )
        return super().eventFilter(watched, event)

    def keyPressEvent(self, event: QKeyEvent) -> None:
        key = event.key()
        if key == Qt.Key_F3:
            on = self.viewport.engine.toggle_perf()
            self.viewport.perf_overlay.setVisible(on)
            return
        if key == Qt.Key_F2:
            self.viewport.engine.toggle_world_debug()
            return
        if key == Qt.Key_Escape:
            if self.map_view.isVisible():
                self.map_view.hide()
                return
            if self.timeline.isVisible() and self.state == AppState.SIMULATION:
                self.timeline.hide()
                return
            if self.state == AppState.CINEMATIC:
                self._exit_cinematic()
                return
            if self.state == AppState.SIMULATION:
                self._set_state(AppState.PAUSED)
                return
            if self.state == AppState.PAUSED:
                self._set_state(AppState.SIMULATION)
                return
            if self.state in (AppState.AIRCRAFT_SELECT, AppState.MISSION_SELECT, AppState.SETTINGS, AppState.REGION_SELECT):
                if self.state == AppState.SETTINGS:
                    self.set_view._on_back()
                    return
                if self.state == AppState.REGION_SELECT:
                    self.viewport.engine.exit_region_preview()
                    self._set_state(AppState.AIRCRAFT_SELECT)
                    return
                self._set_state(AppState.MAIN_MENU)
                return
        if self.state == AppState.SIMULATION:
            action = self.viewport._key_actions.get(key)
            if action == "launch" and not event.isAutoRepeat():
                self.viewport.engine.launch()
                return
            if action == "reset":
                self.viewport.engine.reset_ego()
                return
            if key == Qt.Key_Tab:
                eng = self.viewport.engine
                if eng.hud_layer == "operator":
                    eng.set_hud_layer("flight")
                else:
                    eng.set_hud_layer("operator")
                return
            if key == Qt.Key_M:
                self._toggle_map()
                return
            if key == Qt.Key_P:
                self._set_state(AppState.CINEMATIC)
                return
            if key == Qt.Key_H:
                self.viewport.engine.cycle_hud_layer()
                return
            if key == Qt.Key_F1:
                self.viewport.engine.reset_target()
                return
            if key == Qt.Key_C:
                self.viewport.engine.cycle_camera()
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
        if self.state == AppState.CINEMATIC:
            if key == Qt.Key_P:
                self._exit_cinematic()
                return
            self.viewport.keyPressEvent(event)
            return
        super().keyPressEvent(event)

    def keyReleaseEvent(self, event: QKeyEvent) -> None:
        if self.state in (AppState.SIMULATION, AppState.CINEMATIC):
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
