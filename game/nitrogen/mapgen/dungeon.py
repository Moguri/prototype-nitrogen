import random

import panda3d.core as p3d
from . import bsp
from . import static


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
        if tile_generator == 'bsp':
            tile_generator = bsp
        elif tile_generator == 'static':
            tile_generator = static
        else:
            raise RuntimeError("Unrecognized tile generator {}".format(tile_generator))
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
