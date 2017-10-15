import os
import sys

from direct.showbase.ShowBase import ShowBase
import panda3d.core as p3d
import blenderpanda
from nitrogen import gamestates
from bamboo.inputmapper import InputMapper

if hasattr(sys, 'frozen'):
    APP_ROOT_DIR = os.path.dirname(sys.executable)
else:
    APP_ROOT_DIR = os.path.dirname(__file__)
if not APP_ROOT_DIR:
    print("empty app_root_dir")
    sys.exit()

# prc files to load sorted by load order
CONFIG_ROOT_DIR = os.path.join(APP_ROOT_DIR, 'config')
CONFIG_FILES = [
    os.path.join(CONFIG_ROOT_DIR, 'game.prc'),
    os.path.join(CONFIG_ROOT_DIR, 'user.prc'),
]


for config_file in CONFIG_FILES:
    if os.path.exists(config_file):
        print("Loading config file:", config_file)
        config_file = p3d.Filename.from_os_specific(config_file)
        p3d.load_prc_file(config_file)
    else:
        print("Could not find config file", config_file)


class GameApp(ShowBase):
    def __init__(self):
        ShowBase.__init__(self)
        blenderpanda.init(self)

        self.input_mapper = InputMapper(os.path.join(CONFIG_ROOT_DIR, 'input.conf'))

        self.accept('quit', sys.exit)

        self.disableMouse()
        winprops = self.win.get_properties()
        self.win.move_pointer(0, winprops.get_x_size() // 2, winprops.get_y_size() // 2)
        winprops = p3d.WindowProperties()
        winprops.set_mouse_mode(p3d.WindowProperties.M_confined)
        self.win.request_properties(winprops)

        self.current_state = gamestates.MainState()

        def run_gamestate(task):
            self.current_state.run(p3d.ClockObject.get_global_clock().get_dt())
            return task.cont
        self.taskMgr.add(run_gamestate, 'GameState')

    def change_state(self, next_state):
        self.current_state.cleanup()
        self.current_state = next_state()


def main():
    app = GameApp()
    app.run()


if __name__ == '__main__':
    main()
