white = [1.0, 1.0, 1.0, 1.0]
grey = [0.5, 0.5, 0.5, 1.0]
black = [0.0, 0.0, 0.0, 1.0]
red = [0.5, 0.0, 0.0, 1.0]
green = [0.0, 0.5, 0.0, 1.0]
blue = [0.0, 0.0, 0.5, 1.0]
yellow = [0.5, 0.5, 0.0, 1.0]
purple = [0.5, 0.0, 0.5, 1.0]

clear = [0.0, 0.0, 0.0, 0.0]
menu_bg_color = [0.15, 0.15, 0.15, 1.0]
game_bg_color = [0.25, 0.25, 0.25, 1.0]
tile_color = grey
tile_border_color = [0.7,0.7,0.7,1.0]

die_face_coords = [
    [(0,0),(0,0),(0,0),(0,0),(0,0),(0,0)], #1
    [(-0.5,0.5),(-0.5,0.5),(-0.5,0.5),(0.5,-0.5),(0.5,-0.5),(0.5,-0.5)], #2
    [(-0.5,0.5),(-0.5,0.5),(0,0),(0,0),(0.5,-0.5),(0.5,-0.5)], #3
    [(-0.5,-0.5),(-0.5,0.5),(0.5,0.5),(0.5,-0.5),(0.5,-0.5),(0.5,-0.5)], #4
    [(-0.5,-0.5),(-0.5,0.5),(0.5,0.5),(0.5,-0.5),(0,0),(0,0)], #5
    [(-0.5,-0.5),(-0.5,0.5),(0.5,0.5),(0.5,-0.5),(-0.5,0),(0.5,0)], #6
    ]

def pr(*args):
    print args

def die_face_spot_lookup(center_x, center_y, size_x, size_y, spot_width, spot_height, value, spot):
    try:
        fc = die_face_coords[value - 1][spot - 1]
        return (center_x +fc[0]*size_x/2 - spot_width/2, center_y +fc[1]*size_y/2 - spot_height/2)
    except:
        return (0,0)

def die_face_size(x,y):
    if x is not None:
        return x,y
    else:
        return (0,0)
