import random


def gen(sw, sh, num_encounters=5):
    dungeon = [['.' for _ in range(sw)] for _ in range(sh)]

    # Fill the space with dungeon tiles leaving a one tile empty border
    for y in range(1, sh - 1):
        for x in range (1, sw - 1):
            dungeon[y][x] = '#'

    # Place the start point in the bottom left corner
    dungeon[1][1] = '*'

    # Place the exit in the center
    dungeon[sh // 2][sw // 2] = '&'

    # Place some random encounters
    for _ in range(3):
        tile = ''
        
        while tile != '#':
            x = random.randrange(1, sw - 1)
            y = random.randrange(1, sh - 1)
            tile = dungeon[y][x]

        dungeon[y][x] = '$'


    return dungeon
    
