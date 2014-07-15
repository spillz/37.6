import socket
try:
    import cPickle as pickle
except ImportError:
    import pickle
import struct
import threading

from Queue import Queue

def get_network_ip():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
    s.connect(('<broadcast>', 0))
    return s.getsockname()[0]

class BroadcastServer:
    def __init__(self, game_name, game_port, broadcast_port):
    #UDP server responds to broadcast packets
    #you can have more than one instance of these running
        self.thread = threading.Thread(target = self.broadcast_and_listen)
        self.alive = True
        self.game_name = game_name
        self.game_port = game_port
        self.broadcast_port = broadcast_port
        self.thread.start()
        
    def stop(self):
        self.alive = False
    
    def broadcast_and_listen(self):
        address = ('', self.broadcast_port)
        server_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR,1)
        server_socket.settimeout(1.0)
        server_socket.bind(address)

        while self.alive:
            try:
                recv_data, addr = server_socket.recvfrom(2048,)
                if recv_data == self.game_name:
                    server_socket.sendto(pickle.dumps((self.game_name,self.game_port)), addr)
            except socket.timeout:
                pass

class BroadcastClient:
    def __init__(self, game_name, port, callback):
        self.address = ('<broadcast>', port)
        self.client_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.client_socket.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        self.game_name = game_name
        self.alive = True
        self.callback = callback
        self.responses = {}
        self.thread = threading.Thread(target = self.broadcast)
        self.thread.start()

    def stop(self):
        self.alive = False

    def broadcast(self, timeout = 1.0):
        self.client_socket.settimeout(timeout)
        self.client_socket.sendto(self.game_name, self.address)
        while self.alive:
            try:
                recv_data, addr = self.client_socket.recvfrom(2048)
                self.callback(addr,pickle.loads(recv_data))
                self.responses[addr] = pickle.loads(recv_data)
            except socket.timeout:
                pass
    
'''
Connection, Client and Listener are wrappers around the socket lib
'''

fmt = 'l'
lencoder = lambda value: struct.pack(fmt,value)
lendecoder = lambda string: struct.unpack(fmt,string)[0]
lenc = struct.calcsize(fmt)

class Connection(object):
    def __init__(self, sock, addr, timeout = None):
        self._sock = sock
        if timeout == None:
            self._sock.setblocking(0)
        else:
            self._sock.settimeout(timeout)
        self._addr = addr
        self.send_buffer= ''
        self.recv_buffer = ''
        self.recv_count_buffer = ''
        self.recv_count = 0
        self.recv_finished = True

    def fileno(self):
        return self._sock.fileno()

    def unfinished_send(self):
        return len(self.send_buffer) > 0

    def continue_send(self):
        if len(self.send_buffer) == 0:
            return True
        try:
            wrote = self._sock.send(self.send_buffer)
        except socket.timeout:
            return False
        self.send_buffer = self.send_buffer[wrote:]
        return len(self.send_buffer) == 0

    def continue_recv(self):
        if self.recv_finished:
            return
        self.recv_finished = False
        if len(self.recv_count_buffer) < lenc:
            try:
                self.recv_count_buffer += self._sock.recv(lenc)
            except socket.timeout:
                return
            if len(self.recv_count_buffer) == lenc:
                self.recv_count = lendecoder(self.recv_count_buffer)
#            elif len(self.recv_count_buffer) == 0:
#                raise EOFError
            else:
                return
        ##TODO: check length of count raise exception if too big
        while len(self.recv_buffer) < self.recv_count: ##TRY TO LOOP UNTIL ALL BYTES ARE RECEIVED
            remaining = self.recv_count - len(self.recv_buffer)
            prev_read = len(self.recv_buffer)
            try:
                self.recv_buffer += self._sock.recv(min(remaining,4096))
            except socket.timeout:
                return
            if len(self.recv_buffer) -prev_read < min(remaining, 4096):
                return
        data = pickle.loads(self.recv_buffer)
        self.recv_finished = True
        self.recv_buffer = ''
        self.recv_count_buffer = ''
        return data

    def send(self, data):
        datastream = pickle.dumps(data, -1)
        count = len(datastream)
        ##TODO: check length of count raise exception if too big
        self.send_buffer = lencoder(count) + datastream
        return self.continue_send()

    def recv(self):
        if not self.recv_finished:
            return self.continue_recv()
        self.recv_count_buffer = ''
        self.recv_buffer =''
        self.recv_finished = False
        return self.continue_recv()

    def close(self):
        self._sock.close()

class Listener(object):
    def __init__(self, ip, port, timeout = None):
        self._sock = socket.socket()
        self._sock.setsockopt(socket.SOL_SOCKET,socket.SO_REUSEADDR,1) 
        self.timeout = timeout
        if timeout is None:
            self._sock.setblocking(0)
        else:
            self._sock.settimeout(timeout)
        self._sock.bind((ip, port))
        self._sock.listen(5)
        
    def fileno(self):
        return self._sock.fileno()

    def accept(self):
        return Connection(*self._sock.accept(), timeout = self.timeout)
        
    def close(self):
        self._sock.close()

class Client(Connection):
    def __init__(self, ip, port, timeout = None):
        sock = socket.socket()
        sock.connect((ip, port))
        Connection.__init__(self,sock,(ip, port), timeout)

counter = 0

class Player(object):
    def __init__(self, conn):
        global counter
        self.conn = conn
        self.id = counter
        counter+=1


class ServerConnectionHandler(object):
    '''
    Handles the low level connection handling details of the multiplayer server
    '''
    def __init__(self):
        print('Starting TurnBasedServer on %s:%i'%(SERVER_IP,SERVER_PORT))
        self.listener = Listener(SERVER_IP, SERVER_PORT, 1.0)
        self.players = []
        self.fn_dict = {}

    def register_function(self, name, fn):
        self.fn_dict[name]=fn

    def call_function(self,name,*args):
        return self.fn_dict[name](*args)

    def connections(self):
        return [p.conn for p in self.players]

    def connections_with_comms(self):
        try: #socket version is non-blocking so we need to check for incomplete sends
            return [p.conn for p in self.players if len(p.comms_queue)>0 or p.conn.unfinished_send()]
        except AttributeError: #multiprocessing version is blocking
            return [p.conn for p in self.players if len(p.comms_queue)>0]

    def player_from_connection(self, conn):
        for p in self.players:
            if conn == p.conn:
                return p

    def accept_connection(self):
        conn = self.listener.accept()
        player = Player(conn)
        self.players.append(player)
        return player

    def serve(self):
        alive = True
        while alive:
            r,w,x = select.select([self.listener] + self.connections(), self.connections_with_comms(), [])
            accept_new = True
            for p in self.players:
                if p.conn in r:
                    print('r select for ',p.id,p.name)
                    accept_new = False
                    try:
                        result = p.conn.recv()
                        if result is not None:
                            msg, data = result
                            print('received %s from player %i (%s)'%(msg, p.id, p.name))
                            print(data)
                            if msg == 'quit':
                                alive = False
                            else:
                                try:
                                    self.call_function(msg, p, *data)
                                except Exception as ex:
                                    traceback.print_exc()
                    except EOFError:
                        #TODO: Could allow a few retries before dropping the player
                        print('Disconnect due to EOF error on connection for player %i (%s)'%(p.id,p.name))
                        p.conn.close()
                        self.players.remove(p)
            for p in self.players:
                if p.conn in w:
                    print('w select for ',p.id,p.name)
                    self.dispatch_top_message(p)
            if accept_new and self.listener in r:
                p = self.accept_connection()
                print('connected new player with id %i'%(p.id,))
                self.queue_for_player(p, 'connected', ClientPlayer(p), [ClientPlayer(ap) for ap in self.players])
                self.queue_for_others(p, 'other_player_join', ClientPlayer(p))
        self.listener.close()
        

class ClientConnectionProcess(object):
    '''
    Handles the connection to the multiplayer server in a separate process and routes messages between client and server
    '''
    def __init__(self, client_pipe, SERVER_IP):
        sconn_log('connecting to server at %s:%i',SERVER_IP,SERVER_PORT)
#        self._conn = multiprocessing.connection.Client(address = (SERVER_IP,SERVER_PORT), authkey = 'password')
        self._conn = Client(SERVER_IP,SERVER_PORT)
        self._pipe = client_pipe
        self._server_message_queue = []
        self._client_message_queue = []
        self._players = []

    def register_function(self, name, fn):
        self._fn_dict[name]=fn

    def call_function(self, name, *args):
        return self._fn_dict[name](*args)

    def player_from_id(self, id):
        for p in self._players:
            if id == p.id:
                return p

    def communicate_loop(self):
        alive = True
        while alive:
            w = []
            try:
                if len(self._server_message_queue)>0 or self._conn.unfinished_send()>0:
                    w.append(self._conn)
            except AttributeError: #multiprocessing version is blocking
                if len(self._server_message_queue)>0:
                    w.append(self._conn)
            if len(self._client_message_queue)>0:
                w.append(self._pipe)
            r,w,x = select.select([self._conn, self._pipe], w, [])
            if self._conn in r:
                try:
                    sconn_log('msg from server')
                    result = self._conn.recv()
                    if result is not None:
                        msg, pid, data = result
                        sconn_log('msg from server %s',msg)
                        if msg == 'connected':
                            self.connected(pid, *data)
                        elif msg == 'other_player_join':
                            self.other_player_join(pid, *data)
                        else:
                            p = self.player_from_id(pid)
                            self._client_message_queue.append((msg, data))
                except EOFError:
                    ##TODO: disconnect from server / tell parent / try to reconnect
                    alive = False
            if self._pipe in r:
                msg, data = self._pipe.recv()
                sconn_log('msg from client %s',msg)
                if msg == 'quit':
                    ##TODO: disconnect from server
                    alive = False
                self._server_message_queue.append((msg, data))
            if self._conn in w:
                sconn_log('msg from server %s',msg)
                self.dispatch_top_server_message()
            if self._pipe in w:
                sconn_log('msg from client %s',msg)
                self.dispatch_top_client_message()
        self._conn.close()
        self._pipe.close()

    def connected(self, player_id, player, players):
        '''
        received when the `player` has successfully joined the game
        '''
        self._players = players
        sconn_log('connected %i(%s)', player_id, str(players))
        for p in players:
            if p.id == player_id:
                self.player = p
                self.send_client('connected', p, self._players)
                return

    def other_player_join(self, player_id, player):
        '''
        received when any other `player` has joined the game
        client should add the player to the list of known players
        '''
        self._players.append(player)
        self.send_client('other_player_join', player)

    def dispatch_top_server_message(self):
        try: #socket version is non-blocking so we need to check for incomplete sends
            if self._conn.unfinished_send():
                if not self._conn.continue_send():
                    return
        except AttributeError: #multiprocessing version is blocking so those methods don't exist
            pass
        sconn_log('sending to server %s',self._server_message_queue[0][0])
        self._conn.send(self._server_message_queue.pop(0))

    def dispatch_top_client_message(self):
        sconn_log('sending to client %s',self._client_message_queue[0][0])
        self._pipe.send_bytes(pickle.dumps(self._client_message_queue.pop(0), -1))

    def send_client(self, message, *args):
        self._client_message_queue.append((message, args))

#    '''
#    A simple TCP server for turn based games
#    1. Starts a broadcast connection on BROADCAST_PORT that tells players where to find the game
#    2. Waits for connection by the required number of players
#    3. For each turn, the server will loop over each connected player:
#            a. get request (blocking until it is ready)
#            b. pass request to main thread
#            c. block on players request queue
#            d. send result of request back to player
#    A limitation of the current implementation is that it only listens for a set number of players
#    and will terminate if any player drops
#    '''
class TurnBasedServer(object):
    def __init__(self, GAME_NAME, BROADCAST_PORT, SERVER_PORT, players_required, callback):
        SERVER_IP = get_network_ip()
        print('starting server at %s:%i'%(SERVER_IP,SERVER_PORT))
        self.listener = Listener(SERVER_IP, SERVER_PORT, 1.0)
        self.players = []
        self.fn_dict = {}
        self.players_required = players_required
        self.callback = callback
        self.alive = True
        self.queue = Queue()
        self.listener_thread = threading.Thread(target = self.serve)
        self.listener_thread.start()
        #Start a broadcaster in a separate thread that tells clients the ip:port combination of this server
        self._broadcast_server = BroadcastServer(GAME_NAME, SERVER_PORT, BROADCAST_PORT)

    def connections(self):
        return [p.conn for p in self.players]

    def accept_connection(self):
        conn = self.listener.accept()
        player = Player(conn)
        self.players.append(player)
        return player
    
    def stop(self):
        self.alive = False
        for p in self.players:
            p.queue.put(('_quit',None))
        self._broadcast_server.stop()

    def notify_clients(self, msg, data):
        for p in self.players:
            p.queue.put((msg, data))

    def serve(self):
        while self.alive and len(self.players) < self.players_required:
            try:
                self.accept_connection()
            except socket.error as e:
                pass
            except socket.timeout:
                pass
        if self.alive:
            self.callback('players_joined', None)
            msg, data = self.queue.get()
            for p,d in zip(self.players, data):
                p.id = d
                p.queue = Queue()
            self._broadcast_server.stop()
            for p in self.players: ##TODO: replace this with a select loop
                threading.Thread(target = self._sender, args = (p,)).start()
                threading.Thread(target = self._receiver, args = (p,)).start()
            self.listener.close()

    def _sender(self, p):
        while self.alive:
            msg, data = p.queue.get()
            if not p.conn.send((msg,data)):
                while self.alive and not p.conn.continue_send():
                    pass
        self.alive = False
        
    def _receiver(self, p):
        while self.alive:
            result = p.conn.recv()
            while self.alive and result is None:
                result = p.conn.continue_recv()
            if not self.alive:
                break
            msg, data = result
            if not self.alive:
                break
            self.callback(msg, (p.id, data))
        self.alive=False
        p.conn.close()


class TurnBasedClient(object):
    '''
    Handles the connection to the multiplayer server in a thread and routes messages between client and server
    '''
    def __init__(self, game_name, SERVER_IP, SERVER_PORT, client_callback):
        print('Starting TurnBasedClient on',SERVER_IP, SERVER_PORT)
        self._conn = Client(SERVER_IP, SERVER_PORT, 1.0)
        self._players = []
        self._client_callback = client_callback
        self.alive = True
        self.queue = Queue()
        self.sthread = threading.Thread(target = self._sender)
        self.sthread.start()
        self.rthread = threading.Thread(target = self._receiver)
        self.rthread.start()

    def send(self, msg, data):
        self.queue.put((msg, data))

    def stop(self):
        self.alive = False
        self.queue.put(('quit',None))

    def _sender(self):
        self.alive = True
        while self.alive:
            try:
                msg, data = self.queue.get()
                if not self._conn.send((msg, data)):
                    while self._conn.continue_send(self):
                        pass
            except socket.timeout:
                pass
            except EOFError:
                ##TODO: disconnect from server / tell parent / try to reconnect
                self.alive = False
        self.alive = False
        self._conn.close()
        
    def _receiver(self):
        while self.alive:
            try:
                result = None
                result = self._conn.recv()
                while self.alive and result is None:
                    result = self._conn.continue_recv()
                if not self.alive:
                    break
                msg, data = result
                self._client_callback(msg, data)
            except socket.timeout:
                pass
            except EOFError:
                ##TODO: disconnect from server / tell parent / try to reconnect
                self.alive = False
        self.alive = False


