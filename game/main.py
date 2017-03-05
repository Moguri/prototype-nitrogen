import os
import random
import sys

from direct.showbase.ShowBase import ShowBase
import panda3d.core as p3d
import blenderpanda
import nitrogen.bsp


app_root_dir = sys.path[0]
if not app_root_dir:
    print("emptry app_root_dir")
    sys.exit()

# prc files to load sorted by load order
config_files = [
    os.path.join(app_root_dir, 'config', 'game.prc'),
    os.path.join(app_root_dir, 'config', 'user.prc'),
]


p3d.load_prc_file_data(
    '',
    'framebuffer-srgb true\n'
)


for config_file in config_files:
    if os.path.exists(config_file):
        print("Loading config file:", config_file)
        p3d.load_prc_file(config_file)
    else:
        print("Could not find config file", config_file)


class Dungeon:
    def __init__(self, sizex, sizey):
        self.sizex = sizex
        self.sizey = sizey
        self.model_root = p3d.NodePath('Dungeon')
        self.player_start = p3d.LVector3(0, 0, 0)
        self._telemap = {}
        self.spawners = []

        # Load models
        models = base.loader.load_model('dungeon.bam')
        tile_model = models.find('**/DungeonTile')
        spawn_model = models.find('**/MonsterSpawn')
        tele_model = models.find('**/Teleporter')
        telelink_model = models.find('**/TeleLink')

        # Generate dungeon tile map
        self._bsp = nitrogen.bsp.gen(sizex, sizey)


        # Parse tile map and place models
        for y in range(len(self._bsp)):
            for x in range(len(self._bsp[y])):
                tile = self._bsp[y][x]

                if tile != '.':
                    tilenp = self.model_root.attach_new_node('TileNode')
                    tile_model.instance_to(tilenp)
                    tile_pos = p3d.LVector3(x - sizex / 2.0, y - sizey / 2.0, -random.random() * 0.1)
                    tilenp.set_pos(tile_pos)

                    if tile == '*':
                        # Player start
                        self.player_start.x = tile_pos.x
                        self.player_start.y = tile_pos.y
                    elif tile == '$':
                        # Monster spawn
                        spanwnp = p3d.NodePath('Spawn')
                        spawn_model.instance_to(spanwnp)
                        spanwnp.set_pos(tile_pos + p3d.LVector3(0, 0, 1))
                        spanwnp.set_h(180)
                        self.spawners.append(spanwnp)
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

                            tovec = p3d.LVector3(self._tile_to_world(*self._get_tele_loc_from_tile(x, y)), tlnp.get_z())
                            linkvec = tovec - tlnp.get_pos()

                            tlnp.set_scale(1, linkvec.length(), 1)
                            tlnp.look_at(tovec)

        # Make sure all placed models are visible
        def show_recursive(node):
            node.show()
            for child in node.get_children():
                show_recursive(child)
        show_recursive(self.model_root)
        for spawner in self.spawners:
            show_recursive(spawner)

        # Flatten for performance (we've just place a lot of tile objects that don't move)
        self.model_root.flatten_strong()

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

    def is_walkable(self, x, y):
        tx, ty = self._world_to_tile(x, y)
        tile = self._bsp[ty][tx]
        return tile != '.'


class GameApp(ShowBase):
    PLAYER_SPEED = 15
    CAM_MOVE_BORDER = 0.8
    CAM_MOVE_SPEED  = 50

    def __init__(self):
        ShowBase.__init__(self)
        blenderpanda.init(self)

        self.accept('escape', sys.exit)
        self.accept('mouse1', self.move_player)
        self.accept('f1', self.toggle_debug_cam)

        self.disableMouse()
        wp = self.win.get_properties()
        self.win.move_pointer(0, wp.get_x_size() // 2, wp.get_y_size() // 2)
        wp = p3d.WindowProperties()
        wp.set_mouse_mode(p3d.WindowProperties.M_confined)
        self.win.request_properties(wp)

        dungeon = Dungeon(50, 50)
        dungeon.model_root.reparent_to(self.render)
        for spawner in dungeon.spawners:
            spawner.reparent_to(self.render)

        dlight = p3d.DirectionalLight('sun')
        dlnp = self.render.attach_new_node(dlight)
        dlnp.set_p(-45)
        self.render.set_light(dlnp)

        player = self.loader.load_model('dungeon.bam').find('**/MonsterSpawn').node()
        playernp = dungeon.model_root.attach_new_node(player)
        playernp.set_pos(dungeon.player_start)
        playernp.set_z(1)

        #self.render.ls()

        self.dungeon = dungeon
        self.player = playernp
        self.last_tele_loc = None
        self.target = self.player.get_pos()
        self.debug_cam = False
        self.reset_camera()

        def run_gamestate(task):
            self.update(globalClock.get_dt())
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
            mx, my = self.mouseWatcherNode.get_mouse()
            border = self.CAM_MOVE_BORDER
            camdelta = p3d.LVector2(0, 0)
            if mx < -border:
                camdelta.x -= 1
            elif mx > border:
                camdelta.x += 1

            if my < -border:
                camdelta.y -= 1
            elif my > border:
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


app = GameApp()
app.run()
