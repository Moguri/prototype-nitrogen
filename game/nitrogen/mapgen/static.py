import random


def gen(width, height, num_encounters=5):
    dungeon = [['.' for _ in range(width)] for _ in range(height)]

    # Fill the space with dungeon tiles leaving a one tile empty border
    for y in range(1, height - 1):
        for x in range(1, width - 1):
            dungeon[y][x] = '#'

    # Place the start point in the bottom left corner
    dungeon[1][1] = '*'

    # Place the exit in the center
    dungeon[height // 2][width // 2] = '&'

    # Place some random encounters
    for _ in range(num_encounters):
        tile = ''

        while tile != '#':
            x = random.randrange(1, width - 1)
            y = random.randrange(1, height - 1)
            tile = dungeon[y][x]

        dungeon[y][x] = '$'

    return dungeon
