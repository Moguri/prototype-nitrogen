from collections import namedtuple
import random
import time
import sys


Room = namedtuple('Room', 'x y width height')


class Vertex:
    __slots__ = "vstate", "tile", "coord", "island_idx"

    def __init__(self, vstate, tile, coord, island_idx):
        self.vstate = vstate
        self.tile = tile
        self.coord = coord
        self.island_idx = island_idx


def find_connected_components(dmap):
    graph = {}

    rlimit = sys.getrecursionlimit()
    # print(rlimit, len(dmap)*len(dmap[0]))
    sys.setrecursionlimit(len(dmap) * len(dmap[0]))

    for idxy, tiley in enumerate(dmap):
        for idxx, tilex in enumerate(tiley):
            if tilex in ('#', '$'):
                coord = (idxy, idxx)
                graph[coord] = Vertex(0, tilex, coord, -1)

    def dfs_visit(vert, island_idx):
        def adj():
            vert_list = []

            if dmap[vert.coord[0] + 1][vert.coord[1]] in ('#', '$'):
                vert_list.append(graph[(vert.coord[0] + 1, vert.coord[1])])
            if dmap[vert.coord[0]][vert.coord[1] + 1] in ('#', '$'):
                vert_list.append(graph[(vert.coord[0], vert.coord[1] + 1)])
            if dmap[vert.coord[0] - 1][vert.coord[1]] in ('#', '$'):
                vert_list.append(graph[(vert.coord[0] - 1, vert.coord[1])])
            if dmap[vert.coord[0]][vert.coord[1] - 1] in ('#', '$'):
                vert_list.append(graph[(vert.coord[0], vert.coord[1] - 1)])

            return vert_list

        retval = []

        vert.vstate = 1
        for next_vert in adj():
            if next_vert.vstate == 0:
                retval += dfs_visit(next_vert, island_idx)

        vert.island_idx = island_idx
        vert.vstate = 2
        return retval + [vert]

    island_idx = 0
    connected_components = []
    for vert in graph.values():
        if vert.vstate == 0:
            connected_components.append(dfs_visit(vert, island_idx))
            island_idx += 1

    sys.setrecursionlimit(rlimit)
    return connected_components


def split(startx, starty, endx, endy, min_room_x, min_room_y):
    rangex = endx - startx
    rangey = endy - starty

    if rangex <= min_room_x * 2 or rangey <= min_room_y * 2:
        return [Room(startx, starty, endx, endy)]

    if rangex > rangey:
        # Split x
        part = random.randint(int(rangex * 0.25), int(rangex * 0.75))
        return split(startx, starty, startx + part, endy, min_room_x, min_room_y) + \
            split(startx + part, starty, endx, endy, min_room_x, min_room_y)

    # Split y
    part = random.randint(int(rangey * 0.25), int(rangey * 0.75))
    return split(startx, starty, endx, starty + part, min_room_x, min_room_y) + \
        split(startx, starty + part, endx, endy, min_room_x, min_room_y)


def gen(width, height, min_room_x=5, min_room_y=5, erosion=0.1, num_encounters=5):
    seed = time.time()
    print("Generating dungeon with seed:", seed)
    random.seed(seed)

    dungeon = [['.' for _ in range(width)] for _ in range(height)]
    rooms = []

    rooms = split(1, 1, width - 1, height - 1, min_room_x, min_room_y)

    # Remove half the rooms at random
    rooms = random.sample(rooms, len(rooms)//2)

    num_tiles = 0
    for room in rooms:
        for y in range(room.y, room.height):
            for x in range(room.x, room.width):
                dungeon[y][x] = '#'
                num_tiles += 1

    # Create encounters
    for room in random.sample(rooms, num_encounters):
        # Mutate one tile into an encounter
        y = int((room.height - room.y) * random.gauss(0.5, 0.1) + room.y)
        x = int((room.width - room.x) * random.gauss(0.5, 0.1) + room.x)
        dungeon[y][x] = '$'

    # Erosion
    # Remove x% of tiles
    remaining = int(num_tiles * erosion)
    # print("Eroding", remaining, "tiles")
    while remaining != 0:
        randx = random.randint(0, width - 1)
        randy = random.randint(0, height - 1)

        tile = dungeon[randy][randx]
        if tile not in ('#', '$'):
            continue

        factor = 0.5
        if randy > 0 and dungeon[randy - 1][randx] == '.':
            factor += 1
        if randy < height - 1 and dungeon[randy + 1][randx] == '.':
            factor += 1
        if randx > 0 and dungeon[randy][randx - 1] == '.':
            factor += 1
        if randx < width - 1 and dungeon[randy][randx + 1] == '.':
            factor += 1

        if random.random() * factor > 0.5:
            dungeon[randy][randx] = '.'
            remaining -= 1

    # Connected components
    ccl = find_connected_components(dungeon)
    # print(len(ccl))
    # for island in ccl:
    #     for tile in island:
    #         dungeon[tile.coord[0]][tile.coord[1]] = str(tile.island_idx)

    # Remove islands that are too small
    for island in ccl[:]:
        if len(island) < 5:
            ccl.remove(island)

    # Pick a start tile
    island = random.choice(ccl)
    coord = random.choice(island).coord
    dungeon[coord[0]][coord[1]] = '*'

    # Pick an exit tile
    island = random.choice(ccl)
    coord = random.choice(island).coord
    dungeon[coord[0]][coord[1]] = '&'

    # Place teleporters
    def find_coord(island):
        tile = '.'
        coord = None

        while tile not in ('#', '$'):
            x = random.choice(island)
            tile = x.tile
            coord = x.coord

        return coord

    telcounter = 0
    islands = ccl[:]
    for island in ccl:
        for other in islands:
            if other == island:
                continue
            coord1 = find_coord(island)
            coord2 = find_coord(other)

            dungeon[coord1[0]][coord1[1]] = str(telcounter)
            dungeon[coord2[0]][coord2[1]] = str(telcounter)

            telcounter += 1

        islands.remove(island)

    return dungeon


def _test_gen():
    dungeon = gen(50, 50)

    for y in dungeon:
        for x in y:
            print(x, end=" ")
        print()


if __name__ == '__main__':
    _test_gen()
