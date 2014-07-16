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
    def __init__(self, game_id, game_name, game_port, broadcast_port):
    #UDP server responds to broadcast packets
    #you can have more than one instance of these running
        self.thread = threading.Thread(target = self.broadcast_and_listen)
        self.alive = True
        self.game_id = game_id
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
                recv_data, addr = server_socket.recvfrom(4096,)
                if recv_data == self.game_id:
                    server_socket.sendto(pickle.dumps((self.game_id, self.game_name, self.game_port)), addr)
            except socket.timeout:
                pass

class BroadcastClient:
    def __init__(self, game_id, port, callback):
        self.address = ('<broadcast>', port)
        self.client_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.client_socket.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        self.game_id = game_id
        self.alive = True
        self.callback = callback
        self.responses = {}
        self.thread = threading.Thread(target = self.broadcast)
        self.thread.start()

    def stop(self):
        self.alive = False

    def broadcast(self, timeout = 1.0):
        self.client_socket.settimeout(timeout)
        self.client_socket.sendto(self.game_id, self.address)
        while self.alive:
            try:
                recv_data, addr = self.client_socket.recvfrom(4096)
                try:
                    data = pickle.loads(recv_data)
                    if data[0] == self.game_id:
                        self.responses[addr] = data
                        self.callback(addr,data)
                except:
                    pass
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

class TurnBasedServer(object):
    def __init__(self, GAME_ID, GAME_NAME, BROADCAST_PORT, SERVER_PORT, players_required, callback):
        self.port = SERVER_PORT
        self.players = []
        self.fn_dict = {}
        self.players_required = players_required
        self.callback = callback
        self.alive = True
        self.queue = Queue()
        self.listener_thread = threading.Thread(target = self.serve)
        self.listener_thread.start()
        #Start a broadcaster in a separate thread that tells clients the ip:port combination of this server
        self._broadcast_server = BroadcastServer(GAME_ID, GAME_NAME, SERVER_PORT, BROADCAST_PORT)

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
        try:
            SERVER_IP = get_network_ip()
            print('Starting TurnBasedServer at %s:%i'%(SERVER_IP,self.port))
            self.listener = Listener(SERVER_IP, self.port, 1.0)
            while self.alive and len(self.players) < self.players_required:
                try:
                    self.accept_connection()
                except socket.error as e:
                    pass
                except socket.timeout:
                    pass
        except Exception as e:
            print('Unhandled TurnBasedServer exception')
            import traceback
            traceback.print_exc()
            self.callback('connection_error', e.message)
            self.alive = False
        try:
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
        except Exception as e:
            print('Unhandled TurnBasedServer exception')
            import traceback
            traceback.print_exc()
            self.callback('connection_error', e.message)

    def _sender(self, p):
        try:
            while self.alive:
                msg, data = p.queue.get()
                if not p.conn.send((msg,data)):
                    while self.alive and not p.conn.continue_send():
                        pass
        except Exception as e:
            print('Unhandled TurnBasedServer exception')
            import traceback
            traceback.print_exc()
            self.callback('connection_error', e.message)
        self.alive = False
        
    def _receiver(self, p):
        try:
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
        except Exception as e:
            print('Unhandled TurnBasedServer exception')
            import traceback
            traceback.print_exc()
            self.callback('connection_error', e.message)
        self.alive=False
        p.conn.close()


class TurnBasedClient(object):
    '''
    Handles the connection to the multiplayer server in a thread and routes messages between client and server
    '''
    def __init__(self, game_id, game_name, SERVER_IP, SERVER_PORT, client_callback):
        print('Starting TurnBasedClient on %s:%i'%(SERVER_IP, SERVER_PORT))
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
        try:
            while self.alive:
                try:
                    msg, data = self.queue.get()
                    if not self._conn.send((msg, data)):
                        while self._conn.continue_send(self):
                            pass
                except socket.timeout:
                    pass
#                except EOFError:
#                    ##TODO: disconnect from server / tell parent / try to reconnect
#                    self.alive = False
        except Exception as e:
            print('Unhandled TurnBasedClient exception')
            import traceback
            traceback.print_exc()
            self._client_callback('connection_error', e.message)
        self.alive = False
        self._conn.close()
        
    def _receiver(self):
        try:
            while self.alive:
                try:
                    result = self._conn.recv()
                    while self.alive and result is None:
                        result = self._conn.continue_recv()
                    if not self.alive:
                        break
                    msg, data = result
                    self._client_callback(msg, data)
                except socket.timeout:
                    pass
#                except EOFError:
#                    ##TODO: disconnect from server / tell parent / try to reconnect
#                    self.alive = False
        except Exception as e:
            print('Unhandled TurnBasedClient exception')
            import traceback
            traceback.print_exc()
            self._client_callback('connection_error', e.message)
        self.alive = False


