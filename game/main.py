import os
import random
import sys

from direct.showbase.ShowBase import ShowBase
import panda3d.core as p3d
import blenderpanda
import nitrogen.mapgen.bsp
import nitrogen.mapgen.static
from nitrogen.rangeindicator import RangeIndicator
from bamboo.inputmapper import InputMapper

if hasattr(sys, 'frozen'):
    APP_ROOT_DIR = os.path.dirname(sys.executable)
else:
    APP_ROOT_DIR = os.path.dirname(__file__)
if not APP_ROOT_DIR:
    print("emptry app_root_dir")
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


class Dungeon:
    def __init__(self, tile_generator, sizex, sizey):
        self.sizex = sizex
        self.sizey = sizey
        self.model_root = p3d.NodePath('Dungeon')
        self._tile_root = self.model_root.attach_new_node('Tiles')
        self.player_start = p3d.LVector3(0, 0, 0)
        self._telemap = {}
        self.spawners = []
        self.exit_loc = p3d.LVector3(0, 0, 0)

        # Load models
        loader = p3d.Loader.get_global_ptr()
        models = p3d.NodePath(loader.load_sync('dungeon.bam'))
        for model in models.find_all_matches('**'):
            # Make sure all placed models are visible
            model.show()
        tile_model = models.find('**/DungeonTile')
        spawn_model = models.find('**/MonsterSpawn')
        tele_model = models.find('**/Teleporter')
        telelink_model = models.find('**/TeleLink')

        # Generate dungeon tile map
        self._bsp = tile_generator.gen(sizex, sizey)

        # Parse tile map and place models
        def process_tile(x, y):
            tile = self._bsp[y][x]

            if tile != '.':
                tilenp = self._tile_root.attach_new_node('TileNode')
                tile_model.instance_to(tilenp)
                tile_pos = p3d.LVector3(x - sizex / 2.0, y - sizey / 2.0, -random.random() * 0.1)
                tilenp.set_pos(tile_pos)

                if tile == '*':
                    # Player start
                    self.player_start.x = tile_pos.x
                    self.player_start.y = tile_pos.y
                elif tile == '&':
                    # Exit
                    self.exit_loc.x = tile_pos.x
                    self.exit_loc.y = tile_pos.y

                    exitnp = p3d.NodePath('Exit')
                    tele_model.instance_to(exitnp)
                    exitnp.set_pos(tile_pos + p3d.LVector3(0, 0, 1))
                    exitnp.reparent_to(self.model_root)
                elif tile == '$':
                    # Monster spawn
                    spawnnp = p3d.NodePath('Spawn')
                    spawn_model.instance_to(spawnnp)
                    spawnnp.set_pos(tile_pos + p3d.LVector3(0, 0, 1))
                    spawnnp.set_h(180)
                    spawnnp.reparent_to(self.model_root)
                    self.spawners.append(spawnnp)
                elif tile.isdigit():
                    # Teleporter
                    telenp = self.model_root.attach_new_node('Teleporter')
                    tele_model.instance_to(telenp)
                    telenp.set_pos(tile_pos + p3d.LVector3(0, 0, 1))

                    if tile not in self._telemap:
                        self._telemap[tile] = [(x, y)]
                    else:
                        self._telemap[tile].append((x, y))

                        # This is the second teleporter we found for this pair so add a link
                        tlnp = self.model_root.attach_new_node('TeleporterLink')
                        telelink_model.instance_to(tlnp)
                        tlnp.set_pos(tile_pos + p3d.LVector3(0, 0, 1))

                        teleloc = self._tile_to_world(*self._get_tele_loc_from_tile(x, y))
                        tovec = p3d.LVector3(teleloc, tlnp.get_z())
                        linkvec = tovec - tlnp.get_pos()

                        tlnp.set_scale(1, linkvec.length(), 1)
                        tlnp.look_at(tovec)

        for y in range(len(self._bsp)):
            for x in range(len(self._bsp[y])):
                process_tile(x, y)

        # Flatten for performance (we've just place a lot of tile objects that don't move)
        self._tile_root.flatten_strong()

        # Display the tile map for debugging
        for y in self._bsp:
            for x in y:
                print(x, end=" ")
            print()

    def _tile_to_world(self, x, y):
        return x - self.sizex / 2.0, y - self.sizey / 2.0

    def _world_to_tile(self, x, y):
        return int(x + 0.5 + self.sizex / 2.0), int(y + 0.5 + self.sizey / 2.0)

    def _get_tele_loc_from_tile(self, x, y):
        tile = self._bsp[y][x]

        if not tile.isdigit():
            return None

        return [i for i in self._telemap[tile] if i[0] != x or i[1] != y][0]

    def get_tele_loc(self, x, y):
        loc = self._get_tele_loc_from_tile(*self._world_to_tile(x, y))
        if loc is not None:
            loc = self._tile_to_world(*loc)

        return loc

    def is_exit(self, x, y):
        tilex, tiley = self._world_to_tile(x, y)
        tile = self._bsp[tiley][tilex]
        return tile == '&'

    def is_walkable(self, x, y):
        tilex, tiley = self._world_to_tile(x, y)
        tile = self._bsp[tiley][tilex]
        return tile != '.'


class GameApp(ShowBase):
    PLAYER_SPEED = 15
    CAM_MOVE_BORDER = 0.8
    CAM_MOVE_SPEED = 50

    DUNGEON_SX = 50
    DUNGEON_SY = 50

    def __init__(self):
        ShowBase.__init__(self)
        blenderpanda.init(self)

        self.input_mapper = InputMapper(os.path.join(CONFIG_ROOT_DIR, 'input.conf'))

        self.accept('quit', sys.exit)
        self.accept('toggle-debug-cam', self.toggle_debug_cam)
        self.accept('move', self.move_player)
        self.accept('ability1', self.toggle_range, [0])
        self.accept('ability2', self.toggle_range, [1])
        self.accept('ability3', self.toggle_range, [2])
        self.accept('ability4', self.toggle_range, [3])

        self.disableMouse()
        winprops = self.win.get_properties()
        self.win.move_pointer(0, winprops.get_x_size() // 2, winprops.get_y_size() // 2)
        winprops = p3d.WindowProperties()
        winprops.set_mouse_mode(p3d.WindowProperties.M_confined)
        self.win.request_properties(winprops)

        #self.mapgen = nitrogen.mapgen.bsp;
        self.mapgen = nitrogen.mapgen.static;
        dungeon = Dungeon(self.mapgen, self.DUNGEON_SX, self.DUNGEON_SY)
        dungeon.model_root.reparent_to(self.render)

        dlight = p3d.DirectionalLight('sun')
        dlight.set_color(p3d.LVector3(0.2, 0.2, 0.2))
        #dlight.set_shadow_caster(True, 4096, 4096)
        dlnp = self.render.attach_new_node(dlight)
        dlnp.set_z(10)
        dlnp.set_p(-90)
        lens = dlight.get_lens()
        lens.set_film_size(60)
        lens.set_near(1)
        lens.set_far(100)
        self.render.set_light(dlnp)

        dlight2 = p3d.DirectionalLight('ground')
        dlight2.set_color(p3d.LVector3(0.1, 0.1, 0.1))
        dlnp2 = self.render.attach_new_node(dlight2)
        self.render.set_light(dlnp2)

        player = self.loader.load_model('dungeon.bam').find('**/MonsterSpawn').node()
        playernp = self.render.attach_new_node(player)
        playernp.set_pos(dungeon.player_start)
        playernp.set_z(1.5)
        self.player_ranges = [
            RangeIndicator('box', length=5, width=1),
            RangeIndicator('circle', radius=2),
            RangeIndicator('circle', radius=3),
            RangeIndicator('circle', radius=4),
        ]
        for rangeindicator in self.player_ranges:
            rangeindicator.graphics.reparent_to(playernp)
            rangeindicator.visible = False

        # self.render.ls()
        # self.render.analyze()

        self.dungeons = [dungeon]
        self.dungeon_idx = 0
        self.dungeon = dungeon
        self.player = playernp
        self.last_tele_loc = None
        self.target = self.player.get_pos()
        self.debug_cam = False
        self.reset_camera()

        def run_gamestate(task):
            self.update(p3d.ClockObject.get_global_clock().get_dt())
            return task.cont
        self.taskMgr.add(run_gamestate, 'GameState')

    def toggle_debug_cam(self):
        if not self.debug_cam:
            mat = p3d.LMatrix4(self.camera.get_mat())
            mat.invert_in_place()
            self.mouseInterfaceNode.set_mat(mat)
            self.enableMouse()
            self.debug_cam = True
        else:
            self.disableMouse()
            self.reset_camera()
            self.debug_cam = False

    def toggle_range(self, ability):
        rangeindicator = self.player_ranges[ability]
        rangeindicator.visible = not rangeindicator.visible

    def reset_camera(self):
        campos = self.player.get_pos()
        campos.z += 25
        campos.y -= 25
        self.camera.set_mat(p3d.LMatrix4.ident_mat())
        self.cam.set_pos(campos)
        self.cam.look_at(self.player.get_pos())

    def update(self, dt):
        # Update player position
        movvec = self.target - self.player.get_pos()
        newpos = self.player.get_pos()
        if movvec.length_squared() < 0.4:
            newpos.set_x(self.target.x)
            newpos.set_y(self.target.y)
        else:
            movvec.normalize()
            movvec *= self.PLAYER_SPEED * dt
            newpos.set_x(self.player.get_x() + movvec.x)
            newpos.set_y(self.player.get_y() + movvec.y)
            self.player.look_at(newpos)

        if self.dungeon.is_walkable(*newpos.xy):
            self.player.set_pos(newpos)

        if self.dungeon.is_exit(*newpos.xy):
            next_didx = self.dungeon_idx + 1
            if next_didx >= len(self.dungeons):
                # Create a new dungeon
                self.dungeons.append(Dungeon(self.mapgen, self.DUNGEON_SX, self.DUNGEON_SY))
            self.switch_to_dungeon(next_didx)

        if self.last_tele_loc is not None:
            if (self.last_tele_loc - self.player.get_pos()).length_squared() > 3:
                self.last_tele_loc = None

        if self.last_tele_loc is None:
            teleloc = self.dungeon.get_tele_loc(*newpos.xy)
            if teleloc is not None:
                newpos.x, newpos.y = teleloc
                self.last_tele_loc = p3d.LVector3(newpos)
                self.target = p3d.LVector3(newpos)
                self.player.set_pos(newpos)
                self.reset_camera()

        if not self.debug_cam and self.mouseWatcherNode.has_mouse():
            mousex, mousey = self.mouseWatcherNode.get_mouse()
            border = self.CAM_MOVE_BORDER
            camdelta = p3d.LVector2(0, 0)
            if mousex < -border:
                camdelta.x -= 1
            elif mousex > border:
                camdelta.x += 1

            if mousey < -border:
                camdelta.y -= 1
            elif mousey > border:
                camdelta.y += 1

            camdelta.normalize()
            camdelta *= self.CAM_MOVE_SPEED * dt

            campos = self.cam.get_pos()
            campos.x += camdelta.x
            campos.y += camdelta.y
            self.cam.set_pos(campos)

    def move_player(self):
        if not self.mouseWatcherNode.has_mouse() or self.debug_cam:
            return

        mousevec = self.mouseWatcherNode.get_mouse()
        near = p3d.LPoint3()
        far = p3d.LPoint3()
        self.camLens.extrude(mousevec, near, far)
        near = self.render.get_relative_point(self.cam, near)
        far = self.render.get_relative_point(self.cam, far)

        plane = p3d.Plane(p3d.LVector3.up(), p3d.LPoint3())
        worldpos = p3d.LPoint3()
        if plane.intersects_line(worldpos, near, far):
            self.target.set_x(worldpos.x)
            self.target.set_y(worldpos.y)

    def switch_to_dungeon(self, dungeon_idx):
        # Switch to next layer
        print("Switching to dungeon layer {}".format(dungeon_idx))
        self.dungeon.model_root.detach_node()
        self.dungeon = self.dungeons[dungeon_idx]
        self.dungeon.model_root.reparent_to(self.render)
        self.dungeon_idx = dungeon_idx
        self.player.set_pos(self.dungeon.player_start)
        self.player.set_z(1.5)
        self.target = self.player.get_pos()
        self.reset_camera()


def main():
    app = GameApp()
    app.run()


if __name__ == '__main__':
    main()
