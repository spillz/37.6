'''
37.6 a hex tile game with dice

Game design by Artem Borovkov
Programmed by Damien Moore

See LICENSE for licensing and copyright information
'''
import random
import functools
import kivy
kivy.require('1.0.1')

from kivy.uix.listview import ListView, ListItemLabel, ListItemButton
from kivy.adapters.listadapter import ListAdapter
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.relativelayout import RelativeLayout
from kivy.uix.scatterlayout import ScatterLayout
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.screenmanager import ScreenManager
from kivy.uix.widget import Widget
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.app import App
from kivy.properties import ObjectProperty, StringProperty, ReferenceListProperty, NumericProperty, BooleanProperty, ListProperty
from kivy.uix.image import Image
from kivy.graphics.texture import Texture
from kivy.graphics import Rectangle, Color
from kivy.clock import Clock
from kivy.core.window import Window
from kivy.lang import Builder
from kivy.vector import Vector
from kivy.animation import Animation

from helpers import white, grey, black, clear, game_bg_color, menu_bg_color

game_id = '37.6 v0.3'
game_name = '37.6'
GAME_PORT = 22140
BROADCAST_PORT = 22141

def color_average(a, b, a_wgt = 0.0):
    return (a_wgt*x+(1-a_wgt)*y for x,y in zip(a,b))

class Die(Widget):
    value = NumericProperty()
    spot_width = NumericProperty()
    spot_height = NumericProperty()
    selected = BooleanProperty(False)
    hex_pos_row = NumericProperty()
    hex_pos_col = NumericProperty()
    hex_pos = ReferenceListProperty(hex_pos_col, hex_pos_row)
    die_color = ListProperty()
    spot_color = ListProperty()

    def __init__(self, board, player,
            die_color = [1.0, 0.0, 0.0, 1.0],
            spot_color = [1.0, 1.0, 0.0, 1.0],
             **kwargs):
        super(Die,self).__init__(**kwargs)
        self.board = board
        self.player = player
        self.die_color = die_color
        self.spot_color = spot_color
        self.roll()
        self.hex_pos = [-1,-1] #start off board
        self.bind(selected = self.on_selected)

    def roll(self):
         self.value = random.choice(range(6)) + 1

    def place(self, hex_pos, center_pos):
        if self.selected:
            self.hex_pos = hex_pos
#            self.center = center_pos
            self.selected = False
            a = Animation(center_x = center_pos[0], center_y = center_pos[1], duration = 0.1)
            a.start(self)
            #TODO: Start animation to move die to bottom left

    def on_touch_down(self, touch):
        if self.pos[0]<touch.pos[0]<self.pos[0]+self.size[0] and \
            self.pos[1]<touch.pos[1]<self.pos[1]+self.size[1]:
            if self.board.on_touch_down_die(self, touch):
                return True

    def on_selected(self, obj, value):
        if value == True:
            self.roll()
            self.hex_pos = [-1, -1]
            a = Animation(x = self.board.select_pos[0], y = self.board.select_pos[1], duration = 0.1)
            a.start(self)

class HexTile(Widget):
    hex_width = NumericProperty()
    hex_height = NumericProperty()
    hex_len = NumericProperty()
    hex_pos_x = NumericProperty()
    hex_pos_y = NumericProperty()
    hex_pos = ReferenceListProperty(hex_pos_x, hex_pos_y)
    color = ListProperty()
    default_color = ListProperty()

    def __init__(self, board, **kwargs):
        super(HexTile, self).__init__(**kwargs)
        self.board = board
        self.die = None
        self.default_color = self.color[:]

    def on_touch_down(self, touch):
        if (touch.pos[0] - self.center_x)**2 + (touch.pos[1] - self.center_y)**2 < (self.hex_height/2)**2:
            self.board.on_touch_down_tile(self, touch)

class StatusLabel(Label):
    bg_color = ListProperty()

class Board(FloatLayout):
    board_hex_count = NumericProperty()
    board_width = NumericProperty()
    board_height = NumericProperty()
    hex_width = NumericProperty()
    hex_side = NumericProperty()
    hex_height = NumericProperty()

    def __init__(self):
        super(Board,self).__init__()
        self.bind(board_width = self.size_changed)
        self.tiles = None
        self.selected_die = None
        self.active_player = -1
        self.players = []
        self.scoreboard = ScoreBoard()
        self.add_widget(self.scoreboard)
        self.game_over = False
        self.w_state_label = StatusLabel(text = '', bg_color = clear, color = white, pos_hint ={'right': 0.99, 'y': 0.01})
        self.add_widget(self.w_state_label)

    def remove_players(self):
        self.active_player = -1
        self.selected_die = None
        for p in self.players:
            p.delete()
        self.players = []

    def reset_tiles(self):
        if self.tiles is not None:
            for hp in self.tiles:
                self.remove_widget(self.tiles[hp])
            self.tiles = None

    def setup_game(self, player_spec):
        self.game_over = False
        self.w_state_label.text = ''
        self.w_state_label.color = white
        self.w_state_label.bg_color = clear
        self.remove_players()
        self.reset_tiles()
        if len(player_spec) ==2:
            self.board_hex_count = 7
            dice_count = 12
        elif len(player_spec) == 3:
            self.board_hex_count = 7
            dice_count = 9
        elif len(player_spec) == 4:
            self.board_hex_count = 9
            dice_count = 10
        else: #5
            self.board_hex_count = 9
            dice_count = 9
        for p in player_spec:
            if p.type == 0: #human
                self.players.append(Player(p.name, p.color, self, dice_count))
            if p.type == 1: #computer
                self.players.append(AIPlayer(p.name, p.color, self, dice_count))
            if p.type == 2: #network
                self.players.append(NetworkPlayer(p.name, p.color, self, dice_count))
        self.size_changed()

    def start_game(self):
        self.next_player()

    def next_player(self):
        if self.active_player >= 0:
            self.players[self.active_player].end_turn()
            if max([p.score_marker.score for p in self.players])>=6:
                self.show_game_over()
                return
        self.active_player +=1
        if self.active_player >= len(self.players):
            self.active_player = 0
        p = self.players[self.active_player]
        p.start_turn()
        if p.local_control:
            self.w_state_label.text = 'Select die'
            self.w_state_label.color = color_average(white, p.color)
#            self.w_state_label.bg_color = grey
        else:
            self.w_state_label.text = ''
            self.w_state_label.color = white
#            self.w_state_label.bg_color = clear

    def show_game_over(self):
        scores = [p.score_marker.score for p in self.players]
        hi_score = max(scores)
        winners = [self.players[z] for (z,s) in zip(range(len(self.players)), scores) if s == hi_score]
        self.game_over = True
        if len(winners) == 1:
            self.w_state_label.color = color_average(white, winners[0].color)
            self.w_state_label.text = 'Game over - %s wins'%(winners[0].name)
#            self.w_state_label.bg_color = grey
        else:
            self.w_state_label.color = white
            self.w_state_label.text = 'Game over - draw'
#            self.w_state_label.bg_color = grey

#    def reset_game(self):
#        self.active_player = -1
#        self.selected_die = None
#        for p in self.players:
#            p.reset()
#        for hp in self.tiles:
#            t = self.tiles[hp]
#            t.die = None
#            t.color = t.default_color
#        self.next_player()

    def size_changed(self,*args):
        if self.tiles is None:
            self.tiles = {}
            for x in range(self.board_hex_count):
                y_height = self.board_hex_count - abs((self.board_hex_count-1)//2-x)
                for y in range(y_height):
                    pos = self.pixel_pos((x,y))
                    pos = (pos[0] - self.hex_side, pos[1] - self.hex_side)
                    size = self.hex_width, self.hex_width
                    h= HexTile(self, hex_pos = (x,y), pos = pos, size = size)
                    self.add_widget(h)
                    self.tiles[(x,y)] = h
            self.select_pos = [3*(self.hex_side + 0.01*self.size[0]) , self.size[1] - self.hex_side - 0.01*self.size[0]]
            for p in self.players:
                p.board_resize(self.pos, self.size, self.hex_side)
        else:
            for x in range(self.board_hex_count):
                y_height = self.board_hex_count - abs((self.board_hex_count-1)//2-x)
                for y in range(y_height):
                    pos = self.pixel_pos((x,y))
                    pos = (pos[0] - self.hex_side, pos[1] - self.hex_side)
                    size = self.hex_width, self.hex_width
                    self.tiles[(x,y)].pos = pos
                    self.tiles[(x,y)].size = size
            self.select_pos = [3*(self.hex_side + 0.01*self.size[0]) , self.size[1] - self.hex_side - 0.01*self.size[0]]
            for p in self.players:
                p.board_resize(self.pos, self.size, self.hex_side)
        self.scoreboard.size = (60*len(self.players)+0.01*self.size[0]*(len(self.players)-1), 80)
        self.scoreboard.right = 0.99 * self.size[0]
        self.scoreboard.top = self.size[1] - 0.01*self.size[0]
        self.scoreboard.update_size(self.size)
        self.w_state_label.font_size = 0.04*self.size[1]

    def pixel_pos(self, hex_pos):
        '''
        returns center of hex at position represented by the tuple `hex_pos`
        '''
        return (self.center_x + self.hex_side * 1.5 * (hex_pos[0] - self.board_hex_count//2),
                self.center_y + self.hex_height * (hex_pos[1] - self.board_hex_count//2 + abs(hex_pos[0]-self.board_hex_count//2)/2.0) )

    def hex_pos(self, pixel_pos):
        '''
        returns hex position corresponding to x,y tuple in `pixel_pos`
        '''
        hpos = int((pixel_pos[0] - self.center_x)/(self.hex_side * 1.5) + self.board_hex_count//2 + 0.5)
        vpos = int((pixel_pos[1] - self.center_y)/self.hex_height + self.board_hex_count//2 - abs(hpos-self.board_hex_count//2)//2 + 0.5)
        if 0<=hpos<self.board_hex_count and 0<=vpos<self.board_hex_count:
            return hpos, vpos
        else:
            return None

    def neighbor_iter(self, hex_pos):
        y_offset_left = hex_pos[0]<=self.board_hex_count//2
        y_offset_right = hex_pos[0]>=self.board_hex_count//2
        for x,y in [(0,-1), (0,+1), (-1,-y_offset_left), (-1,+1-y_offset_left), (+1,-y_offset_right), (+1,+1-y_offset_right)]:
            try:
                yield self.tiles[(hex_pos[0]+x,hex_pos[1]+y)]
            except KeyError:
                pass

    def get_neighbor_count(self, hex_pos):
        value = 0
        for t in self.neighbor_iter(hex_pos):
            if t.die is not None:
                value += 1
        return value

    def update_tile_and_neighbors(self,tile):
        if tile.die is not None and tile.die.value == self.get_neighbor_count(tile.hex_pos):
            color = tile.die.die_color[:]
            color[0] = (1.0+color[0])/2.0
            color[1] = (1.0+color[1])/2.0
            color[2] = (1.0+color[2])/2.0
            tile.color = color
        else:
            tile.color = tile.default_color
        for t in self.neighbor_iter(tile.hex_pos):
            if t.die is not None:
                if t.die.value == self.get_neighbor_count(t.hex_pos):
                    color = t.die.die_color[:]
                    color[0] = (1.0+color[0])/2.0
                    color[1] = (1.0+color[1])/2.0
                    color[2] = (1.0+color[2])/2.0
                    t.color = color
                else:
                    t.color = t.default_color

    def update_scores(self):
        for p in self.players:
            score = 0
            for d in p.dice:
                if d.hex_pos != [-1, -1]:
                    t = self.tiles[(d.hex_pos[0], d.hex_pos[1])]
                    if t.color != t.default_color:
                        score +=1
            p.score_marker.score = score

    def place_die(self, tile, server_check = True):
        '''
        called by touch handler for local player, or by AI or network
        player to place the selected die on a tile
        '''
        if not self.game_over and self.selected_die is not None:
            hex_pos = tile.hex_pos
            if self.tiles[(hex_pos[0], hex_pos[1])].die is not None:
                return
            if server_check:
                try:
                    if self.server is not None:
                        self.server.send('place', (self.active_player, (int(hex_pos[0]), int(hex_pos[1]))))
                        return True
                except AttributeError:
                    pass
            center_pos = self.pixel_pos(hex_pos)
            self.selected_die.place(hex_pos, center_pos)
            self.tiles[(hex_pos[0], hex_pos[1])].die = self.selected_die
            self.update_tile_and_neighbors(tile)
            self.update_scores()
            self.selected_die = None
            self.next_player()
            #NOTIFY NETWORK PLAYERS ABOUT THE MOVE
            try:
                if self.server is not None:
                    self.server.notify_clients('s_place', (self.active_player, (int(hex_pos[0]), int(hex_pos[1]))))
            except AttributeError:
                pass

    def select_die(self, die, roll_value = None):
        '''
        called by touch handler for local player, or by AI or network
        player to select a die
        '''
        if not self.game_over and self.selected_die is None and die in self.players[self.active_player].dice:
            dice = self.players[self.active_player].dice
            die_num = dice.index(die)
            if roll_value is None:
                try:
                    if self.server is not None:
                        self.server.send('select', (self.active_player, die_num))
                        return True
                except AttributeError:
                    pass
            if die.hex_pos != [-1, -1]:
                t = self.tiles[(die.hex_pos[0], die.hex_pos[1])]
                t.die = None
                self.update_tile_and_neighbors(t)
                self.update_scores()
            die.selected = True
            if roll_value is not None:
                die.value = roll_value
            self.selected_die = die
            #NOTIFY NETWORK PLAYERS ABOUT THE MOVE
            try:
                if self.server is not None:
                    self.server.notify_clients('s_select', (self.active_player, die_num, die.value))
                return True
            except AttributeError:
                pass
        return False


    def on_touch_down_tile(self, tile, touch):
        if self.game_over:
            return True
        if not self.players[self.active_player].local_control:
            return True
        return self.place_die(tile)

    def on_touch_down_die(self, die, touch):
        if self.game_over:
            return True
        p = self.players[self.active_player]
        if not p.local_control:
            return True
        else:
            self.w_state_label.text = 'Place die'
            self.w_state_label.color = color_average(white, p.color)
#            self.w_state_label.bg_color = grey
        return self.select_die(die)

class ScoreBoard(BoxLayout):
    def __init__(self):
        super(ScoreBoard, self).__init__(orientation = 'horizontal')
    def update_size(self, board_size):
        self.spacing = 0.01*board_size[0]

class PlayerScore(FloatLayout):
    ident = StringProperty()
    color = ListProperty()
    score = NumericProperty()
    active_turn = BooleanProperty(False)
    def __init__(self, identity, color):
        super(PlayerScore, self).__init__()
        self.ident = identity
        self.color = color

class Player(object):
    def __init__(self, name, color, board, dice_count = 12):
        self.local_control = True
        self.name = name
        self.color = color
        self.board = board
        self.dice_count = dice_count
        self.dice = [Die(board, self, die_color = color) for x in range(dice_count)]
        self.score_marker = PlayerScore(identity = self.name[0:2], color = color)
        self.board.scoreboard.add_widget(self.score_marker)

    def delete(self):
        self.reset()
        self.board.scoreboard.remove_widget(self.score_marker)
        for d in self.dice:
            if d.parent is not None:
                self.board.remove_widget(d)

    def reset(self):
        self.score_marker.active_turn = False
        self.score_marker.score = 0
        for x,d in zip(range(self.dice_count),self.dice):
            if d.hex_pos != [-1, -1]:
                self.board.remove_widget(d)
            d.hex_pos = [-1, -1]
            d.selected = False
            hex_side = self.board.hex_side
            board_size = self.board.size
            d.pos = (x%2 * (hex_side + 0.01*board_size[0]),
                     board_size[1] - (1 + x//2) * (hex_side + 0.01*board_size[0]))

    def start_turn(self):
        self.score_marker.active_turn = True
        for d in self.dice:
            if d.hex_pos == [-1, -1]:
                self.board.add_widget(d)

    def end_turn(self):
        self.score_marker.active_turn = False
        for d in self.dice:
            if d.hex_pos == [-1, -1]:
                self.board.remove_widget(d)

    def board_resize(self, pos, board_size, hex_side):
        for x, d in zip(range(self.dice_count), self.dice):
            d.size = (hex_side, hex_side)
            if d.hex_pos != [-1, -1]:
                d.center = self.board.pixel_pos(d.hex_pos)
            else:
                if d.selected:
                    d.pos = self.board.select_pos
                else:
                    d.pos = (x%2 * (hex_side + 0.01*board_size[0]),
                             board_size[1] - (1 + x//2) * (hex_side + 0.01*board_size[0]))

class AIPlayer(Player):
    def __init__(self, name, color, board, dice_count = None):
        super(AIPlayer, self).__init__(name, color, board, dice_count)
        self.local_control = False

    def score_add_die(self, value, hex_pos):
        placed = len([t for t in self.board.neighbor_iter(hex_pos) if t.die is not None])
        score = value - placed
        if score == 0:
            score = 2
        elif score > 0 and placed > 0:
            score = 1
        elif score < 0:
            score = -1
        else:
            score = 0
        return score

    def score_remove_die(self, value, hex_pos):
        placed = len([t for t in self.board.neighbor_iter(hex_pos) if t.die is not None])
        score = value - placed
        if score == 0:
            score = -2
        elif score == 1:
            score = 2
        elif score > 1 and placed > 0:
            score = -1
        elif score < 0:
            score = 1
        else:
            score = 0
        return score

    def score_remove_neighbor(self, value, hex_pos):
        placed = len([t for t in self.board.neighbor_iter(hex_pos) if t.die is not None])
        score = value - placed
        if score == -1: #remove to lock die is good
            score = 2
        elif score == 0: #removing from a locked die is bad
            score = -2
        elif score < -1 and placed > 0: #removing a die that already has neigbors is good
            score = 1
        elif score > 0: #adding a die that already has too many neighbors is bad
            score = -1
        else:
            score = 0
        return score

    def score_add_neighbor(self, value, hex_pos):
        placed = len([t for t in self.board.neighbor_iter(hex_pos) if t.die is not None])
        score = value - placed
        if score == 0: #adding to a locked die is bad
            score = -2
        elif score == 1: #adding to lock a die is good
            score = 2
        elif score > 1 and placed > 0: #adding a die that already has neigbors is good
            score = 1
        elif score < 0: #adding a die that already has too many neighbors is bad
            score = -1
        else:
            score = 0
        return score

    def start_turn(self):
        super(AIPlayer, self).start_turn()
        Clock.schedule_once(self.select_turn, 0.7)

    def select_turn(self, *args):
        die = self.evaluate_die_select()
        print('selecting',die.hex_pos)
        self.board.select_die(die)
        Clock.schedule_once(self.place_turn, 0.7)

    def place_turn(self, *args):
        tile = self.evaluate_die_place()
        print('placing',tile.hex_pos)
        self.board.place_die(tile)

    def evaluate_die_select(self):
        #TODO: if this takes time, chunk it up and call repeatedly using a timer
        select_scores = []
        print('die_select')
        for x,d in zip(range(self.dice_count), self.dice):
            if d.hex_pos != [-1, -1]:
                score = self.score_remove_die(d.value, d.hex_pos) ##TODO: incentive to do this is not strong while score is low
                if score>0:
                    score=0
                self.board.neighbor_iter(d.hex_pos)
                for t in self.board.neighbor_iter(d.hex_pos):
                    if t.die is not None:
                        if t.die.player == self:
                            score += self.score_remove_neighbor(t.die.value, t.die.hex_pos) ##TODO: only give weight to players with scores above, say, 4
                        else:
                            if t.die.player.score_marker.score > 3:
                                score -= self.score_remove_neighbor(t.die.value, t.die.hex_pos)
            else: #prefer to select dice from the stack if opponents scores are low enough
                if max([p.score_marker.score for p in self.board.players])>4:
                    score = 0
                else:
                    score = 2
            print(d.hex_pos,score)
            select_scores.append(score)
        max_score = max(select_scores)
        candidates = [self.dice[x] for x in range(self.dice_count) if select_scores[x] == max_score]
        print(max_score)
        return random.choice(candidates)

    def evaluate_die_place(self):
        #TODO: if this takes time, chunk it up and call repeatedly using a timer
        value = self.board.selected_die.value
        max_score = -1000
        candidates = []
#        print('die_place')
        for hp in self.board.tiles:
            t = self.board.tiles[hp]
            if t.die is None:
                score = self.score_add_die(value, hp)
#                print score,
                n = list(self.board.neighbor_iter(hp))
                if value > len(n) and score > 0:
                    score -= 2
#                    print score,
                for t1 in n:
                    if t1.die is not None:
                        if t1.die.player == self:
                            score += self.score_add_neighbor(t1.die.value, t1.die.hex_pos) ##TODO: only give weight to players with scores above, say, 4
#                            print score,
                        else:
                            score -= self.score_add_neighbor(t1.die.value, t1.die.hex_pos)
#                            print score,
                if score == max_score:
                    candidates.append(t)
                elif score > max_score:
                    candidates = [t]
                    max_score = score
 #               print hp, score
 #       print max_score
        return random.choice(candidates)


class NetworkPlayer(Player):
    def __init__(self, name, color, board, dice_count = None):
        super(NetworkPlayer, self).__init__(name, color, board, dice_count)
        self.local_control = False
        self.queue = None

    def start_turn(self):
        super(NetworkPlayer, self).start_turn()


class GameScreen(BoxLayout):
    def __init__(self):
        super(GameScreen, self).__init__()
        self.board = Board()
        self.add_widget(self.board)

class PlayerSpec:
    def __init__(self, name, color, type):
        self.name = name
        self.color = color
        self.type = type

color_lookup = {
    0: [0.6, 0, 0, 1],
    1: [0, 0.6, 0, 1],
    2: [0, 0, 0.6, 1],
    3: [0.5, 0, 0.5, 1],
    4: [0.5, 0.5, 0, 1],
    }

class GameMenu(ScreenManager):
    player_count = NumericProperty()
    players = ListProperty()
    disconnected = BooleanProperty()
    w_game = ObjectProperty()
    w_start_button = ObjectProperty()
    w_join_button = ObjectProperty()
    w_join_game_box = ObjectProperty()
    w_join_game_adapter = ObjectProperty()

    def __init__(self):
        super(GameMenu, self).__init__()
        self.w_start_button.bind(on_release = self.start_game)
        self.w_join_button.bind(on_release = self.find_network_game)

        args_converter = lambda row_index, rec: {'text': '%s on %s:%s'%(rec['game_name'],str(rec['ip_address']),str(rec['port'])) ,
            'size_hint_y': 0.1}
        adapter = ListAdapter(data = [],
            args_converter=args_converter,
            cls=ListItemButton,
            selection_mode='single',
            allow_empty_selection=True)
        self.w_join_game_list_view = ListView(size_hint = (0.6, 0.6), pos_hint = {'center_x':0.5, 'center_y':0.6},
                    adapter = adapter)
        self.w_join_game_box.add_widget(self.w_join_game_list_view)
        self.w_join_game_list_view.adapter.bind(on_selection_change = self.network_game_join)

        self.player_spec = []
        self.server = None
        self.disconnected = False

    def find_network_game(self, *args):
        print('looking for network games')
        import msocket
        self.w_join_game_list_view.adapter.data = []
        self.server = msocket.BroadcastClient(game_id, BROADCAST_PORT, callback = self.network_broadcaster_callback)
        self.current = 'join_game'

    def stop_server(self):
        if self.server is not None:
            self.server.stop()
            self.server = None

    def network_broadcaster_callback(self, *args):
        Clock.schedule_once(functools.partial(self.network_game_found, *args))

    def network_game_found(self, *args):
        (ip, bport), (game_id, game_name, gport), dt = args
        data = self.w_join_game_list_view.adapter.data[:]
        data.append({'ip_address': ip, 'game_name': game_name, 'port': gport})
        self.w_join_game_list_view.adapter.data = data
        self.w_join_game_list_view.populate()

    def network_game_join(self, adapter):
        if len(adapter.selection) == 0:
            return
        sel = adapter.selection[0]
        data = adapter.data[sel.index]
        gname = data['game_name']
        ip = data['ip_address']
        gport = data['port']
        import msocket
        self.stop_server()
        try:
            self.server = msocket.TurnBasedClient(game_id, gname, ip, gport, self.server_callback)
        except:
            #TODO: NOTIFY USER THAT CLIENT COULDN'T CONNECT
            return
        self.disconnected = False
        self.server.send('hello',None)
    
    def start_network_server(self):
        import msocket
        self.server = msocket.TurnBasedServer(game_id, game_name, BROADCAST_PORT, GAME_PORT, self.num_network_players, callback = self.server_callback)
        self.disconnected = False

    def server_callback(self, *args):
        Clock.schedule_once(functools.partial(self.server_msg, *args))
        
    def server_msg(self, *args):
        msg, data, dt = args
        board = self.w_game.children[0]
        if msg == 'players_joined': #all players have joined
            net_players = [x for x in range(self.player_count) if self.players[x]==2]
            self.server.queue.put(('player_ids',net_players))
            self.start_network_game(self.player_spec)
        elif msg == 'hello': #remote player says hello, send the initial game data
            player_id, data = data
            players_id = [x for x in range(len(board.players))]
            board.players[player_id].queue.put(('s_hello', (player_id, players_id)))
        elif msg == 's_hello': #data contains this players id and a list of player id's in turn order
            player_id, players_id = data
            spec = []
            for x in range(len(players_id)):
                ps = PlayerSpec('Player '+str(x), color_lookup[x], 0 if players_id[x] == player_id else 2)
                spec.append(ps)
            self.start_network_game(spec)
        elif msg == 'select': #player wants to select a die
            player_id, (pid, die_num) = data
            p = board.players[pid]
            die = p.dice[die_num]
            board.select_die(die)
            #self.server.send(player_id, True, die_num, die.value)
        elif msg == 's_select': #notify player whether they have selected a die and the roll result
            player_id, die_num, roll_value = data
            p = board.players[player_id]
            die = p.dice[die_num]
            board.select_die(die, roll_value)
        elif msg == 'place': #player wants to place a die
            player_id, (pid, hex_pos) = data
            t = board.tiles[hex_pos]
            board.place_die(t)
            #self.server.send(True, hex_pos)
        elif msg == 's_place': #notify player whether the die has been placed
            success, hex_pos = data
            t = board.tiles[hex_pos]
            board.place_die(t, False)
        elif msg == 's_restart': #resposne to the game restart
            #    data is success
            self.start_network_game()
        elif msg == 's_quitgame': #response to the game quit
            #    data is success
            self.server.stop()
            self.server = None
            self.current = 'main'
        elif msg == 'connection_error':
            board.w_state_label.color = white
#            board.w_state_label.bg_color = grey
            board.w_state_label.text = 'Disconnected - game over'
            board.game_over = True
            self.server = None
            self.disconnected = True

    def start_network_game(self, spec = None):
        if spec is not None:
            self.player_spec = spec
        board = self.w_game.children[0]    
        board.server = self.server
        board.setup_game(self.player_spec)
        board.start_game()
        self.current = 'game'
        try:
            net_players = [x for x in range(self.player_count) if self.players[x]==2]
            for x in range(len(net_players)):
                board.players[net_players[x]].queue = self.server.players[x].queue
        except AttributeError:
            pass

    def restart_game(self):
        if self.disconnected:
            return False
        if self.server is not None:
            try:
                self.server.notify_clients('s_restart',None)
            except AttributeError:
                return False
        board = self.w_game.children[0]    
        board.setup_game(self.player_spec)
        board.start_game()
        try:
            net_players = [x for x in range(self.player_count) if self.players[x]==2]
            for x in range(len(net_players)):
                board.players[net_players[x]].queue = self.server.players[x].queue
        except AttributeError:
            pass
        self.current = 'game'
        
    def join_game(self, *args):
        pass

    def start_game(self, *args):
        self.player_spec = []
        self.num_network_players = 0
        for x in range(self.player_count):
            ps = PlayerSpec('Player '+str(x+1), color_lookup[x], self.players[x])
            if ps.type == 2:
                self.num_network_players += 1
            self.player_spec.append(ps)
        if self.num_network_players > 0:
            self.start_network_server()
            self.current = 'host_wait'
        else:
            board = self.w_game.children[0]
            board.server = None
            board.setup_game(self.player_spec)
            board.start_game()
            self.current = 'game'

class GameApp(App):
    def build(self):
        self.gm = GameMenu()
        self.gm.w_game.add_widget(Board())
        Window.bind(on_keyboard = self.on_keyboard)
        return self.gm

    def on_keyboard(self, window, key, scancode=None, codepoint=None, modifier=None):
        '''
        used to manage the effect of the escape key
        '''
        if key == 27:
            if self.gm.current == 'main':
                return False
            elif self.gm.current == 'host_game':
                self.gm.current = 'main'
            elif self.gm.current == 'host_wait':
                self.gm.stop_server(); 
                self.gm.current = 'main'
            elif self.gm.current == 'join_game':
                self.gm.stop_server(); 
                self.gm.current = 'main'
            elif self.gm.current == 'game':
                self.gm.current = 'pause'
            elif self.gm.current == 'pause':
                self.gm.current = 'game'
            return True
        return False

    def on_pause(self):
        '''
        trap on_pause to keep the app alive on android
        '''
        return True

    def on_resume(self):
        pass

    def on_stop(self):
        print('app stop')
        if self.gm.server is not None:
            self.gm.server.stop()

if __name__ == '__main__':
    Builder.load_file('376.kv')
    gameapp = GameApp()
    gameapp.run()
