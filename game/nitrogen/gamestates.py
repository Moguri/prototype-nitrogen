from direct.showbase.DirectObject import DirectObject
import panda3d.core as p3d

from .mapgen.dungeon import Dungeon
from .rangeindicator import RangeIndicator


class GameState(DirectObject):
    def __init__(self):
        super().__init__()
        self.root_node = p3d.NodePath('State Root')
        self.root_node.reparent_to(base.render)

    def cleanup(self):
        self.ignoreAll()
        self.root_node.remove_node()
        self.root_node = None

    def run(self, dt):
        pass


class MainState(GameState):
    PLAYER_SPEED = 15
    CAM_MOVE_BORDER = 0.8
    CAM_MOVE_SPEED = 50

    DUNGEON_SX = 50
    DUNGEON_SY = 50

    def __init__(self):
        super().__init__()

        self.accept('toggle-debug-cam', self.toggle_debug_cam)
        self.accept('move', self.move_player)
        self.accept('ability1', self.toggle_range, [0])
        self.accept('ability2', self.toggle_range, [1])
        self.accept('ability3', self.toggle_range, [2])
        self.accept('ability4', self.toggle_range, [3])

        self.mapgen = 'static'
        dungeon = Dungeon(self.mapgen, self.DUNGEON_SX, self.DUNGEON_SY)
        dungeon.model_root.reparent_to(self.root_node)

        dlight = p3d.DirectionalLight('sun')
        dlight.set_color(p3d.LVector3(0.2, 0.2, 0.2))
        dlight.set_shadow_caster(True, 4096, 4096)
        dlnp = self.root_node.attach_new_node(dlight)
        dlnp.set_z(10)
        dlnp.set_p(-90)
        lens = dlight.get_lens()
        lens.set_film_size(60)
        lens.set_near(1)
        lens.set_far(100)
        self.root_node.set_light(dlnp)

        dlight2 = p3d.DirectionalLight('ground')
        dlight2.set_color(p3d.LVector3(0.1, 0.1, 0.1))
        dlnp2 = self.root_node.attach_new_node(dlight2)
        self.root_node.set_light(dlnp2)

        loader = p3d.Loader.get_global_ptr()
        player = p3d.NodePath(loader.load_sync('dungeon.bam')).find('**/MonsterSpawn').node()
        playernp = self.root_node.attach_new_node(player)
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

        # self.root_node.ls()
        # self.root_node.analyze()

        self.dungeons = [dungeon]
        self.dungeon_idx = 0
        self.dungeon = dungeon
        self.player = playernp
        self.last_tele_loc = None
        self.target = self.player.get_pos()
        self.debug_cam = False
        self.reset_camera()

    def toggle_debug_cam(self):
        if not self.debug_cam:
            mat = p3d.LMatrix4(base.camera.get_mat())
            mat.invert_in_place()
            base.mouseInterfaceNode.set_mat(mat)
            base.enableMouse()
            self.debug_cam = True
        else:
            base.disableMouse()
            self.reset_camera()
            self.debug_cam = False

    def toggle_range(self, ability):
        rangeindicator = self.player_ranges[ability]
        rangeindicator.visible = not rangeindicator.visible

    def reset_camera(self):
        campos = self.player.get_pos()
        campos.z += 25
        campos.y -= 25
        base.camera.set_mat(p3d.LMatrix4.ident_mat())
        base.cam.set_pos(campos)
        base.cam.look_at(self.player.get_pos())

    def run(self, dt):
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

        if not self.debug_cam and base.mouseWatcherNode.has_mouse():
            mousex, mousey = base.mouseWatcherNode.get_mouse()
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

            campos = base.cam.get_pos()
            campos.x += camdelta.x
            campos.y += camdelta.y
            base.cam.set_pos(campos)

    def move_player(self):
        if not base.mouseWatcherNode.has_mouse() or self.debug_cam:
            return

        mousevec = base.mouseWatcherNode.get_mouse()
        near = p3d.LPoint3()
        far = p3d.LPoint3()
        base.camLens.extrude(mousevec, near, far)
        near = self.root_node.get_relative_point(base.cam, near)
        far = self.root_node.get_relative_point(base.cam, far)

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
        self.dungeon.model_root.reparent_to(self.root_node)
        self.dungeon_idx = dungeon_idx
        self.player.set_pos(self.dungeon.player_start)
        self.player.set_z(1.5)
        self.target = self.player.get_pos()
        self.reset_camera()
