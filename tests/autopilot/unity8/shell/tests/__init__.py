# -*- Mode: Python; coding: utf-8; indent-tabs-mode: nil; tab-width: 4 -*-
#
# Unity Autopilot Test Suite
# Copyright (C) 2012, 2013, 2014, 2015 Canonical
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
#

"""unity autopilot tests."""

try:
    from gi.repository import Gio
except ImportError:
    Gio = None

from autopilot import introspection
from autopilot.platform import model
from autopilot.testcase import AutopilotTestCase
from autopilot.matchers import Eventually
from autopilot.input import Touch
from autopilot.display import Display
import logging
import os.path
import subprocess
import sys
import evdev
from testtools.matchers import Equals
from ubuntuuitoolkit import (
    fixture_setup as toolkit_fixtures,
    ubuntu_scenarios
)

from unity8 import (
    get_lib_path,
    get_binary_path,
    get_mocks_library_path,
    get_default_extra_mock_libraries,
    get_data_dirs
)
from unity8 import (
    fixture_setup,
    process_helpers
)
from unity8.shell import emulators
from unity8.shell.emulators import (
    dash as dash_helpers,
    main_window as main_window_emulator,
)


logger = logging.getLogger(__name__)

UNITYSHELL_GSETTINGS_SCHEMA = "org.compiz.unityshell"
UNITYSHELL_GSETTINGS_PATH = "/org/compiz/profiles/unity/plugins/unityshell/"
UNITYSHELL_LAUNCHER_KEY = "launcher-hide-mode"
UNITYSHELL_LAUNCHER_MODE = 1  # launcher hidden


def _get_device_emulation_scenarios(devices='All'):
    nexus4 = ('Desktop Nexus 4',
              dict(app_width=768, app_height=1280, grid_unit_px=18))
    nexus10 = ('Desktop Nexus 10',
               dict(app_width=2560, app_height=1600, grid_unit_px=20))
    native = ('Native Device',
              dict(app_width=0, app_height=0, grid_unit_px=0))

    if model() == 'Desktop':
        if devices == 'All':
            return [nexus4, nexus10]
        elif devices == 'Nexus4':
            return [nexus4]
        elif devices == 'Nexus10':
            return [nexus10]
        else:
            raise RuntimeError(
                'Unrecognized device-option "%s" passed.' % devices
            )
    else:
        return [native]


def is_unity7_running():
    """Return True if Unity7 is running. Otherwise, return False."""
    return (
        Gio is not None and
        UNITYSHELL_GSETTINGS_SCHEMA in
        Gio.Settings.list_relocatable_schemas()
    )


def get_qml_import_path_with_mock():
    """Return the QML2_IMPORT_PATH value with the mock path prepended."""
    qml_import_path = [get_mocks_library_path()]
    if os.getenv('QML2_IMPORT_PATH') is not None:
        qml_import_path.append(os.getenv('QML2_IMPORT_PATH'))

    qml_import_path = ':'.join(qml_import_path)
    logger.info("New QML2 import path: %s", qml_import_path)
    return qml_import_path


class UnityTestCase(AutopilotTestCase):

    """A test case base class for the Unity shell tests."""

    @classmethod
    def setUpClass(cls):
        try:
            output = subprocess.check_output(
                ["/sbin/initctl", "status", "unity8"],
                stderr=subprocess.STDOUT,
                universal_newlines=True,
            )
        except subprocess.CalledProcessError as e:
            sys.stderr.write(
                "Error: `initctl status unity8` failed, most probably the "
                "unity8 session could not be found:\n\n"
                "{0}\n"
                "Please install unity8 or copy data/unity8.conf to "
                "{1}\n".format(
                    e.output,
                    os.path.join(os.getenv("XDG_CONFIG_HOME",
                                           os.path.join(os.getenv("HOME"),
                                                        ".config")
                                           ),
                                 "upstart")
                    )
            )
            sys.exit(1)

        if "start/" in output:
            sys.stderr.write(
                "Error: Unity is currently running, these tests require it to "
                "be 'stopped'.\n"
                "Please run this command before running these tests: \n"
                "initctl stop unity8\n"
            )
            sys.exit(2)

    def setUp(self):
        super().setUp()
        if is_unity7_running():
            self.useFixture(toolkit_fixtures.HideUnity7Launcher())

        self._proxy = None
        self._qml_mock_enabled = True
        self._data_dirs_mock_enabled = True
        self._environment = {}

        # FIXME: This is a work around re: lp:1238417
        if model() != "Desktop":
            from autopilot.input import _uinput
            _uinput._touch_device = _uinput.create_touch_device()
            self.addCleanup(_uinput._touch_device.close)

        self.uinput = evdev.UInput(name='unity8-autopilot-power-button',
                                   devnode='/dev/autopilot-uinput')
        self.touch = Touch.create()
        self._setup_display_details()

    def _setup_display_details(self):
        scale_divisor = self._determine_geometry()
        self._setup_grid_size(scale_divisor)

    def _determine_geometry(self):
        """Use the geometry that may be supplied or use the default."""
        width = getattr(self, 'app_width', 0)
        height = getattr(self, 'app_height', 0)
        scale_divisor = 1
        self.unity_geometry_args = []
        if width > 0 and height > 0:
            if self._geo_larger_than_display(width, height):
                scale_divisor = self._get_scaled_down_geo(width, height)
                width = width / scale_divisor
                height = height / scale_divisor
                logger.info(
                    "Geometry larger than display, scaled down to: %dx%d",
                    width,
                    height
                )
            geo_string = "%dx%d" % (width, height)
            self.unity_geometry_args = [
                '-windowgeometry',
                geo_string,
                '-frameless',
                '-mousetouch'
            ]
        return scale_divisor

    def _setup_grid_size(self, scale_divisor):
        """Use the grid size that may be supplied or use the default."""
        if getattr(self, 'grid_unit_px', 0) == 0:
            self.grid_size = int(os.getenv('GRID_UNIT_PX'))
        else:
            self.grid_size = int(self.grid_unit_px / scale_divisor)
            self._environment["GRID_UNIT_PX"] = str(self.grid_size)

    def _geo_larger_than_display(self, width, height):
        should_scale = getattr(self, 'scale_geo', True)
        if should_scale:
            screen = Display.create()
            screen_width = screen.get_screen_width()
            screen_height = screen.get_screen_height()
            return (width > screen_width) or (height > screen_height)
        else:
            return False

    def _get_scaled_down_geo(self, width, height):
        divisor = 1
        while self._geo_larger_than_display(width / divisor, height / divisor):
            divisor = divisor * 2
        return divisor

    def _patch_environment(self, key, value):
        """Wrapper for patching env for upstart environment."""
        try:
            current_value = subprocess.check_output(
                ["/sbin/initctl", "get-env", "--global", key],
                stderr=subprocess.STDOUT,
                universal_newlines=True,
            ).rstrip()
        except subprocess.CalledProcessError:
            current_value = None

        subprocess.call([
            "/sbin/initctl",
            "set-env",
            "--global",
            "%s=%s" % (key, value)
        ], stderr=subprocess.STDOUT)
        self.addCleanup(self._upstart_reset_env, key, current_value)

    def _upstart_reset_env(self, key, value):
        logger.info("Resetting upstart env %s to %s", key, value)
        if value is None:
            subprocess.call(
                ["/sbin/initctl", "unset-env", key],
                stderr=subprocess.STDOUT,
            )
        else:
            subprocess.call([
                "/sbin/initctl",
                "set-env",
                "--global",
                "%s=%s" % (key, value)
            ], stderr=subprocess.STDOUT)

    def launch_unity(self, **kwargs):
        """Launch the unity shell, return a proxy object for it."""
        binary_path = get_binary_path()
        lib_path = get_lib_path()

        logger.info(
            "Lib path is '%s', binary path is '%s'",
            lib_path,
            binary_path
        )

        self.patch_lightdm_mock()

        if self._qml_mock_enabled:
            self._environment['QML2_IMPORT_PATH'] = (
                get_qml_import_path_with_mock()
            )

        if self._data_dirs_mock_enabled:
            self._patch_data_dirs()

        # FIXME: we shouldn't be doing this
        # $MIR_SOCKET, fallback to $XDG_RUNTIME_DIR/mir_socket and
        # /tmp/mir_socket as last resort
        try:
            os.unlink(
                os.getenv('MIR_SOCKET',
                          os.path.join(os.getenv('XDG_RUNTIME_DIR', "/tmp"),
                                       "mir_socket")))
        except OSError:
            pass
        try:
            os.unlink("/tmp/mir_socket")
        except OSError:
            pass

        app_proxy = self._launch_unity_with_upstart(
            binary_path,
            self.unity_geometry_args,
        )

        self._set_proxy(app_proxy)

        # Ensure that the dash is visible before we return:
        logger.debug("Unity started, waiting for it to be ready.")
        self.wait_for_unity()
        logger.debug("Unity loaded and ready.")

        if model() == 'Desktop':
            # On desktop, close the dash because it's opened in a separate
            # window and it gets in the way.
            process_helpers.stop_job('unity8-dash')

        return app_proxy

    def _launch_unity_with_upstart(self, binary_path, args):
        logger.info("Starting unity")
        self._patch_environment("QT_LOAD_TESTABILITY", 1)

        binary_arg = "BINARY=%s" % binary_path
        extra_args = "ARGS=%s" % " ".join(args)
        env_args = ["%s=%s" % (k, v) for k, v in self._environment.items()]
        all_args = [binary_arg, extra_args] + env_args

        self.addCleanup(self._cleanup_launching_upstart_unity)

        return process_helpers.restart_unity_with_testability(*all_args)

    def _cleanup_launching_upstart_unity(self):
        logger.info("Stopping unity")
        try:
            subprocess.check_output(
                ["/sbin/initctl", "stop", "unity8"],
                stderr=subprocess.STDOUT
            )
        except subprocess.CalledProcessError:
            logger.warning("Appears unity was already stopped!")

    def _patch_data_dirs(self):
        data_dirs = get_data_dirs(self._data_dirs_mock_enabled)
        if data_dirs is not None:
            self._environment['XDG_DATA_DIRS'] = data_dirs

    def patch_lightdm_mock(self):
        logger.info("Setting up LightDM mock lib")
        new_ld_library_path = [
            get_default_extra_mock_libraries(),
            self._get_lightdm_mock_path()
        ]
        if os.getenv('LD_LIBRARY_PATH') is not None:
            new_ld_library_path.append(os.getenv('LD_LIBRARY_PATH'))

        new_ld_library_path = ':'.join(new_ld_library_path)
        logger.info("New library path: %s", new_ld_library_path)

        self._environment['LD_LIBRARY_PATH'] = new_ld_library_path

    def _get_lightdm_mock_path(self):
        lib_path = get_mocks_library_path()
        lightdm_mock_path = os.path.abspath(
            os.path.join(lib_path, "LightDM", "liblightdm")
        )

        if not os.path.exists(lightdm_mock_path):
            raise RuntimeError(
                "LightDM mock does not exist at path '%s'."
                % (lightdm_mock_path)
            )
        return lightdm_mock_path

    def _set_proxy(self, proxy):
        """Keep a copy of the proxy object, so we can use it to get common
        parts of the shell later on.

        """
        self._proxy = proxy
        self.addCleanup(self._clear_proxy)

    def _clear_proxy(self):
        self._proxy = None

    def wait_for_unity(self):
        greeter = self.main_window.wait_select_single(objectName='greeter')
        greeter.waiting.wait_for(False)

    def get_dash(self):
        pid = process_helpers.get_job_pid('unity8-dash')
        dash_proxy = introspection.get_proxy_object_for_existing_process(
            pid=pid,
            emulator_base=emulators.UnityEmulatorBase,
        )
        dash_app = dash_helpers.DashApp(dash_proxy)
        return dash_app.dash

    def lock_unity(self):
        """Helper function that attempts to lock the unity greeter."""
        import time
        # One press and release to turn screen off (locking unity)
        self.uinput.write(evdev.ecodes.EV_KEY, evdev.ecodes.KEY_POWER, 1)
        self.uinput.write(evdev.ecodes.EV_KEY, evdev.ecodes.KEY_POWER, 0)
        self.uinput.syn()
        time.sleep(1)
        # And another press and release to turn screen back on
        self.uinput.write(evdev.ecodes.EV_KEY, evdev.ecodes.KEY_POWER, 1)
        self.uinput.write(evdev.ecodes.EV_KEY, evdev.ecodes.KEY_POWER, 0)
        self.uinput.syn()

    @property
    def main_window(self):
        return self._proxy.select_single(main_window_emulator.QQuickView)


class DashBaseTestCase(AutopilotTestCase):

    scenarios = ubuntu_scenarios.get_device_simulation_scenarios()
    qml_mock_enabled = True
    environment = {}

    def setUp(self):
        super().setUp()

        if is_unity7_running():
            self.useFixture(toolkit_fixtures.HideUnity7Launcher())

        if model() != 'Desktop':
            # On the phone, we need unity to be running and unlocked.
            self.addCleanup(process_helpers.stop_job, 'unity8')
            process_helpers.restart_unity_with_testability()
            process_helpers.unlock_unity()

        self.ensure_dash_not_running()

        if self.qml_mock_enabled:
            self.environment['QML2_IMPORT_PATH'] = (
                get_qml_import_path_with_mock()
            )

        if self.should_simulate_device():
            # This sets the grid units, so it should be called before launching
            # the app.
            self.simulate_device()

        binary_path = get_binary_path('unity8-dash')
        dash_proxy = self.launch_dash(binary_path, self.environment)

        self.dash_app = dash_helpers.DashApp(dash_proxy)
        self.dash = self.dash_app.dash
        self.wait_for_dash()

    def ensure_dash_not_running(self):
        if process_helpers.is_job_running('unity8-dash'):
            process_helpers.stop_job('unity8-dash')

    def launch_dash(self, binary_path, variables):
        launch_dash_app_fixture = fixture_setup.LaunchDashApp(
            binary_path, variables)
        self.useFixture(launch_dash_app_fixture)
        return launch_dash_app_fixture.application_proxy

    def wait_for_dash(self):
        home_scope = self.dash.get_scope_by_index(0)
        # FIXME! There is a huge timeout here for when we're doing CI on
        # VMs. See lp:1203715
        self.assertThat(
            home_scope.isLoaded,
            Eventually(Equals(True), timeout=60)
        )
        self.assertThat(home_scope.isCurrent, Eventually(Equals(True)))

    def should_simulate_device(self):
        return (hasattr(self, 'app_width') and hasattr(self, 'app_height') and
                hasattr(self, 'grid_unit_px'))

    def simulate_device(self):
        simulate_device_fixture = self.useFixture(
            toolkit_fixtures.SimulateDevice(
                self.app_width, self.app_height, self.grid_unit_px))
        self.environment['GRID_UNIT_PX'] = simulate_device_fixture.grid_unit_px
        self.environment['ARGS'] = '-windowgeometry {0}x{1}'\
            .format(simulate_device_fixture.app_width,
                    simulate_device_fixture.app_height)
