import os
import random
import sys

from direct.showbase.ShowBase import ShowBase
import panda3d.core as p3d
import blenderpanda
import nitrogen.bsp

p3d.load_prc_file_data(
    '',
    'framebuffer-srgb true\n'
)

class Dungeon:
    def __init__(self, sizex, sizey):
        models = base.loader.load_model('dungeon.bam')
        tile_model = models.find('**/DungeonTile')
        bsp = nitrogen.bsp.gen(sizex, sizey)

        self.model_root = p3d.NodePath('Dungeon')
        self.player_start = p3d.LVector3(0, 0, 0)

        for y in range(len(bsp)):
            for x in range(len(bsp[y])):
                tile = bsp[y][x]

                if tile != '.':
                    tilenp = self.model_root.attach_new_node('TileNode')
                    tile_model.instance_to(tilenp)
                    tile_pos = p3d.LVector3(x - sizex / 2.0, y - sizey / 2.0, -random.random() * 0.1)
                    tilenp.set_pos(tile_pos)

                    if tile == '*':
                        self.player_start.x = tile_pos.x
                        self.player_start.y = tile_pos.y


        def show_recursive(node):
            node.show()
            for child in node.get_children():
                show_recursive(child)
        show_recursive(self.model_root)
        self.model_root.flatten_strong()

        for y in bsp:
            for x in y:
                print(x, end=" ")
            print()


class GameApp(ShowBase):
    def __init__(self):
        ShowBase.__init__(self)
        blenderpanda.init(self)
        self.accept('escape', sys.exit)
        self.accept('mouse1', self.move_player)

        dungeon = Dungeon(50, 50)
        dungeon.model_root.reparent_to(self.render)

        dlight = p3d.DirectionalLight('sun')
        dlnp = self.render.attach_new_node(dlight)
        dlnp.set_pos(0, 0, 1)
        dlnp.look_at(0, 0, 0)
        self.render.set_light(dlnp)

        alight = p3d.AmbientLight('amb')
        alight.set_color(p3d.LVector3(0.2, 0.2, 0.2))
        alnp = self.render.attach_new_node(alight)
        self.render.set_light(alnp)

        player = self.loader.load_model('dungeon.bam').find('**/MonsterSpawn').node()
        playernp = dungeon.model_root.attach_new_node(player)
        playernp.set_pos(dungeon.player_start)
        playernp.set_z(1)

        #self.render.ls()

        self.dungeon = dungeon
        self.player = playernp

    def move_player(self):
        if not self.mouseWatcherNode.has_mouse():
            return

        mousevec = self.mouseWatcherNode.get_mouse()
        near = p3d.LPoint3()
        far = p3d.LPoint3()
        self.camLens.extrude(mousevec, near, far)
        near = self.render.get_relative_point(self.camera, near)
        far = self.render.get_relative_point(self.camera, far)

        plane = p3d.Plane(p3d.LVector3.up(), p3d.LPoint3())
        worldpos = p3d.LPoint3()
        if plane.intersects_line(worldpos, near, far):
            self.player.set_x(worldpos.x)
            self.player.set_y(worldpos.y)


app = GameApp()
app.run()
