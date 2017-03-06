from collections import namedtuple
import random
import time
import sys


class V:
    __slots__ = "vstate", "tile", "coord", "cc"

    def __init__(self, vstate, tile, coord, cc):
        self.vstate = vstate
        self.tile = tile
        self.coord = coord
        self.cc = cc


def dfs(dmap):
    G = {}

    rlimit = sys.getrecursionlimit()
    # print(rlimit, len(dmap)*len(dmap[0]))
    sys.setrecursionlimit(len(dmap) * len(dmap[0]))

    for iy, vy in enumerate(dmap):
        for ix, vy in enumerate(vy):
            if vy in ('#', '$'):
                coord = (iy, ix)
                G[coord] = V(0, vy, coord, -1)

    cc = 0
    connected_components = []
    for v in G.values():
        if v.vstate == 0:
            connected_components.append(dfs_visit(dmap, G, v, cc))
            cc += 1

    sys.setrecursionlimit(rlimit)
    return connected_components


def dfs_visit(dmap, G, V, cc):
    def adj(dmap, G, V):
        vl = []

        if dmap[V.coord[0] + 1][V.coord[1]] in ('#', '$'):
            vl.append(G[(V.coord[0] + 1, V.coord[1])])
        if dmap[V.coord[0]][V.coord[1] + 1] in ('#', '$'):
            vl.append(G[(V.coord[0], V.coord[1] + 1)])
        if dmap[V.coord[0] - 1][V.coord[1]] in ('#', '$'):
            vl.append(G[(V.coord[0] - 1, V.coord[1])])
        if dmap[V.coord[0]][V.coord[1] - 1] in ('#', '$'):
            vl.append(G[(V.coord[0], V.coord[1] - 1)])

        return vl

    retval = []

    V.vstate = 1
    for v in adj(dmap, G, V):
        if v.vstate == 0:
            retval += dfs_visit(dmap, G, v, cc)

    V.cc = cc
    V.vstate = 2
    return retval + [V]


Room = namedtuple('Room', 'x y sw sh')


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
    else:
        # Split y
        part = random.randint(int(rangey * 0.25), int(rangey * 0.75))
        return split(startx, starty, endx, starty + part, min_room_x, min_room_y) + \
            split(startx, starty + part, endx, endy, min_room_x, min_room_y)


def gen(sw, sh, min_room_x=5, min_room_y=5, erosion=0.1, num_encounters=5):
    seed = time.time()
    print("Generating dungeon with seed:", seed)
    random.seed(seed)

    dungeon = [['.' for _ in range(sw)] for _ in range(sh)]
    rooms = []

    rooms = split(1, 1, sw - 1, sh - 1, min_room_x, min_room_y)

    # Remove half the rooms at random
    rooms = random.sample(rooms, len(rooms)//2)

    num_tiles = 0
    for room in rooms:
        for y in range(room.y, room.sh):
            for x in range(room.x, room.sw):
                dungeon[y][x] = '#'
                num_tiles += 1

    # Create encounters
    for room in random.sample(rooms, num_encounters):
        # Mutate one tile into an encounter
        y = int((room.sh - room.y) * random.gauss(0.5, 0.1) + room.y)
        x = int((room.sw - room.x) * random.gauss(0.5, 0.1) + room.x)
        dungeon[y][x] = '$'

    # Erosion
    # Remove x% of tiles
    remaining = int(num_tiles * erosion)
    #print("Eroding", remaining, "tiles")
    while remaining != 0:
        rx = random.randint(0, sw - 1)
        ry = random.randint(0, sh - 1)

        tile = dungeon[ry][rx]
        if tile not in ('#', '$'):
            continue

        factor = 0.5
        if ry > 0 and dungeon[ry - 1][rx] == '.':
            factor += 1
        if ry < sh - 1 and dungeon[ry + 1][rx] == '.':
            factor += 1
        if rx > 0 and dungeon[ry][rx - 1] == '.':
            factor += 1
        if rx < sw - 1 and dungeon[ry][rx + 1] == '.':
            factor += 1

        if random.random() * factor > 0.5:
            dungeon[ry][rx] = '.'
            remaining -= 1

    # Connected components
    ccl = dfs(dungeon)
    #print(len(ccl))
    #for cc in ccl:
    #    for tile in cc:
    #        dungeon[tile.coord[0]][tile.coord[1]] = str(tile.cc)

    # Remove islands that are too small
    for cc in ccl[:]:
        if len(cc) < 5:
            ccl.remove(cc)

    # Pick a start tile
    cc = random.choice(ccl)
    coord = random.choice(cc).coord
    dungeon[coord[0]][coord[1]] = '*'

    # Place teleporters
    def find_coord(cc):
        tile = '.'
        coord = None

        while tile not in ('#', '$'):
            x = random.choice(cc)
            tile = x.tile
            coord = x.coord

        return coord

    telcounter = 0
    islands = ccl[:]
    for cc in ccl:
        for other in islands:
            if other == cc:
                continue
            c1 = find_coord(cc)
            c2 = find_coord(other)

            dungeon[c1[0]][c1[1]] = str(telcounter)
            dungeon[c2[0]][c2[1]] = str(telcounter)

            telcounter += 1

        islands.remove(cc)

    return dungeon

if __name__ == '__main__':
    d = gen(50, 50)

    for y in d:
        for x in y:
            print(x, end=" ")
        print()
