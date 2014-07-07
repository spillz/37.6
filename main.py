'''
37.6 a hex tile game with dice

Game design by Artem Borovkov
Programmed by Damien Moore

See LICENSE for licensing and copyright information
'''
import random
import kivy
kivy.require('1.0.1')

from kivy.uix.floatlayout import FloatLayout
from kivy.uix.relativelayout import RelativeLayout
from kivy.uix.scatterlayout import ScatterLayout
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.screenmanager import ScreenManager
from kivy.uix.widget import Widget
from kivy.uix.popup import Popup
from kivy.uix.button import Button
from kivy.app import App
from kivy.properties import ObjectProperty, StringProperty, ReferenceListProperty, NumericProperty, BooleanProperty, ListProperty
from kivy.uix.image import Image
from kivy.graphics.texture import Texture
from kivy.graphics import Rectangle, Color
from kivy.clock import Clock
from kivy.lang import Builder
from kivy.vector import Vector

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
    
    def __init__(self, board, 
            die_color = [1.0, 0.0, 0.0, 1.0], 
            spot_color = [1.0, 1.0, 0.0, 1.0],
             **kwargs):
        super(Die,self).__init__(**kwargs)
        self.board = board
        self.value = random.choice(range(6))
        self.die_color = die_color
        self.spot_color = spot_color
        self.hex_pos = [-1,-1] #start off board
        self.bind(selected = self.on_selected)
    
    def roll(self):
        self.value = random.choice(range(6))
    
    def place(self, hex_pos, center_pos):
        if self.selected:
            self.hex_pos = hex_pos
            self.center = center_pos
            self.selected = False
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
            self.pos = self.board.select_pos

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

    def remove_players(self):
        self.active_player = -1
        self.selected_die = None
        for p in self.players:
            p.delete()
        self.players = []
        
    def add_players(self, player_spec):
        self.remove_players()
        if len(player_spec)==2:
            self.board_hex_count = 7
        else:
            self.board_hex_count = 9
        for p in player_spec:
            if p.type == 0: #human
                self.players.append(Player(p.name, p.color, self))
            if p.type == 1: #computer
                self.players.append(AIPlayer(p.name, p.color, self))
            if p.type == 2: #network
                self.players.append(NetworkPlayer(p.name, p.color, self))
        self.size_changed()
    
    def start_game(self):
        self.next_player()

    def next_player(self):
        if self.active_player >= 0:
            self.players[self.active_player].end_turn()
            if self.players[self.active_player].score_marker.score>=6:
                self.show_game_over()
                return
        self.active_player +=1
        if self.active_player >= len(self.players):
            self.active_player = 0
        self.players[self.active_player].start_turn()

    def show_game_over(self):
        scores = [p.score_marker.score for p in self.players]
        hi_score = max(scores)
        winners = [self.players[z].name for (z,s) in zip(range(len(self.players)), scores) if s == hi_score]
        g = GameOver(board = self, winner_names = winners, size = (self.size[0]/2, self.size[1]/2))
        g.open()

    def exit_game(self):
        gameapp.stop()

    def reset_game(self):
        self.active_player = -1
        self.selected_die = None
        for p in self.players:
            p.reset()
        for hp in self.tiles:
            t = self.tiles[hp]
            t.die = None
            t.color = t.default_color
        self.next_player()

    def size_changed(self,*args):
        if self.tiles is None:
            self.tiles = {}
            for x in range(self.board_hex_count):
                for y in range(self.board_hex_count - abs((self.board_hex_count-1)/2-x)):
                    pos = self.pixel_pos((x,y))
                    pos = (pos[0] - self.hex_side, pos[1] - self.hex_side)
                    size = self.hex_width, self.hex_width
                    h= HexTile(self, hex_pos = (x,y), pos = pos, size = size)
                    self.add_widget(h)
                    self.tiles[(x,y)] = h
            self.select_pos = [3*(self.hex_side + 0.01*self.size[0]) , self.size[1] - self.hex_side - 0.01*self.size[0]]
            for p in self.players:
                p.board_resize(self.pos, self.size, self.hex_side)
#            self.next_player()
        else:
            for x in range(self.board_hex_count):
                for y in range(self.board_hex_count - abs((self.board_hex_count-1)/2-x)):
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
        
    def pixel_pos(self, hex_pos):
        '''
        returns center of hex at position represented by the tuple `hex_pos`
        '''
        return (self.center_x + self.hex_side * 1.5 * (hex_pos[0] - self.board_hex_count/2), 
                self.center_y + self.hex_height * (hex_pos[1] - self.board_hex_count/2 + abs(hex_pos[0]-self.board_hex_count/2)/2.0) )
        
    def hex_pos(self, pixel_pos):
        '''
        returns hex position corresponding to x,y tuple in `pixel_pos`
        '''
        hpos = int((pixel_pos[0] - self.center_x)/(self.hex_side * 1.5) + self.board_hex_count/2 + 0.5)
        vpos = int((pixel_pos[1] - self.center_y)/self.hex_height + self.board_hex_count/2 - abs(hpos-self.board_hex_count/2)/2 + 0.5)
        if 0<=hpos<self.board_hex_count and 0<=vpos<self.board_hex_count:
            return hpos, vpos
        else:
            return None

    def neighbor_iter(self, hex_pos):
        y_offset_left = hex_pos[0]<=self.board_hex_count/2
        y_offset_right = hex_pos[0]>=self.board_hex_count/2
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
        if tile.die is not None and tile.die.value + 1 == self.get_neighbor_count(tile.hex_pos):
            color = tile.die.die_color[:]
            color[0] = (1.0+color[0])/2.0
            color[1] = (1.0+color[1])/2.0
            color[2] = (1.0+color[2])/2.0
            tile.color = color
        else:
            tile.color = tile.default_color
        for t in self.neighbor_iter(tile.hex_pos):
            if t.die is not None: 
                if t.die.value + 1 == self.get_neighbor_count(t.hex_pos):
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

    def on_touch_down_tile(self, tile, touch):
        if self.selected_die is not None:
            hex_pos = tile.hex_pos
            if self.tiles[(hex_pos[0], hex_pos[1])].die is not None:
                return
            center_pos = self.pixel_pos(hex_pos)
            self.selected_die.place(hex_pos, center_pos)
            self.tiles[(hex_pos[0], hex_pos[1])].die = self.selected_die
            self.update_tile_and_neighbors(tile)
            self.update_scores()
            self.selected_die = None
            self.next_player()
         
    def on_touch_down_die(self, die, touch):
        if self.selected_die is None and die in self.players[self.active_player].dice:
            if die.hex_pos != [-1, -1]:
                t = self.tiles[(die.hex_pos[0], die.hex_pos[1])]
                t.die = None
                self.update_tile_and_neighbors(t)                
                self.update_scores()
            die.selected = True
            self.selected_die = die
            return True
        return False

class GameOver(Popup):
    winner_names = ListProperty()

    def __init__(self, board, winner_names, **kwargs):
        super(GameOver, self).__init__(**kwargs)
        self.board = board
        self.winner_names = winner_names

    def on_exit(self, *args):
        self.dismiss()
        self.board.exit_game()

    def on_replay(self, *args):
        self.dismiss()
        self.board.reset_game()
    
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

class Player:
    def __init__(self, name, color, board):
        self.local_control = True
        self.name = name
        self.color = color
        self.board = board
        self.die_count = 12
        self.dice = [Die(board, die_color = color) for x in range(12)]
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
        for x,d in zip(range(self.die_count),self.dice):
            if d.hex_pos != [-1, -1]:
                self.board.remove_widget(d)
            d.hex_pos = [-1, -1]
            d.selected = False
            hex_side = self.board.hex_side
            board_size = self.board.size
            d.pos = (x%2 * (hex_side + 0.01*board_size[0]),
                     board_size[1] - (1 + x/2) * (hex_side + 0.01*board_size[0]))

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
        for x, d in zip(range(self.die_count), self.dice):
            d.size = (hex_side, hex_side)
            if d.hex_pos != [-1, -1]:
                d.center = self.board.pixel_pos(d.hex_pos)
            else:
                if d.selected:
                    d.pos = self.board.select_pos
                else:
                    d.pos = (x%2 * (hex_side + 0.01*board_size[0]),
                             board_size[1] - (1 + x/2) * (hex_side + 0.01*board_size[0]))

class AIPlayer(Player):
    def __init__(self, name, color, board):
        super(AIPlayer, self).__init__(self, name, color, board)
        self.local_control = False

    def evaluate_choose(self):
        self.choose_score = {}
        for d in self.die:
            pass

    def evaluate_place(self):
        self.scoreable = {}
        for hp in self.board.tiles:
            self.scoreable[hp] = self.board.neighbor_iter(hp)

    def choose_die(self):
        '''
        tells player to choose a die
        '''
        pass
    
    def place_die(self):
        '''
        tells player to place his selected die
        '''
        pass
    
class NetworkPlayer(Player):
    def __init__(self, name, color, board):
        super(NetworkPlayer, self).__init__(self, name, color, board)
        self.local_control = False

    def choose_die(self):
        '''
        tells player to choose a die
        '''
        pass
    
    def place_die(self):
        '''
        tells player to place his selected die
        '''
        pass

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
    w_game = ObjectProperty()
    w_start_button = ObjectProperty()
    
    def __init__(self):
        super(GameMenu, self).__init__()
        self.w_start_button.bind(on_release = self.start_game)
        
    def start_game(self, *args):
        player_spec = []
        for x in range(self.player_count):
            player_spec.append(PlayerSpec('Player '+str(x+1), color_lookup[x], self.players[x]))
        self.w_game.children[0].add_players(player_spec)
        self.w_game.children[0].start_game()
        self.current = 'game'

class GameApp(App):
    def build(self):
        gm = GameMenu()
        gm.w_game.add_widget(Board())
        return gm

if __name__ == '__main__':
    Builder.load_file('376.kv')
    gameapp = GameApp()
    gameapp.run()
