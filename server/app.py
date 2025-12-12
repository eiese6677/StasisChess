# server/app.py
from flask import Flask, request
from flask_socketio import SocketIO, emit, join_room
import copy
import uuid

app = Flask(__name__)
app.config['SECRET_KEY'] = 'dev'
socketio = SocketIO(app, cors_allowed_origins="*")

class Piece:
    def __init__(self, id, type, color, pos=None):
        self.id = id
        self.type = type            # 'pawn','rook','knight','bishop','queen','king'
        self.color = color          # 'w' or 'b'
        self.pos = pos              # (x,y) or None
        self.stun = 0
        self.move_stack = 0
        self.captured = (pos is None)

    def to_json(self):
        return {
            "id": self.id,
            "type": self.type,
            "color": self.color,
            "pos": list(self.pos) if self.pos is not None else None,
            "stun": self.stun,
            "move_stack": self.move_stack,
            "captured": self.captured
        }

    # 각 기물 클래스에서 오버라이드
    def can_move(self, frm, to, board):
        print("오버라이드 필요")
        return False

    def drop(self, pos):
        self.pos = pos
        self.captured = False
        self.stun = 1
        self.move_stack = 0

    def capture(self, target):
        # 만약 스택이 쌓여있는 기물을 잡았을 경우, 그 스택이 잡은 기물에게 이전된다.
        self.stun += target.stun
        self.move_stack += target.move_stack

    def end_turn(self):
        # 이동 스텍은 스턴 스텍이 턴을 넘겨서 1씩 사라질 때마다 1씩 늘어난다.
        if self.pos is None:
            return
        if self.stun > 0:
            self.stun -= 1
            self.move_stack += 1

class Knight(Piece):
    def __init__(self, id, color, pos=None):
        super().__init__(id, 'knight', color, pos)

    def can_move(self, frm, to, board):
        dx = abs(frm[0]-to[0]); dy = abs(frm[1]-to[1])
        return (dx==1 and dy==2) or (dx==2 and dy==1)

class Rook(Piece):
    def __init__(self, pid, color, pos=None):
        super().__init__(pid, 'rook', color, pos)

    def can_move(self, frm, to, board):
        if frm[0]!=to[0] and frm[1]!=to[1]: return False
        dx = 0 if frm[0]==to[0] else (1 if to[0]>frm[0] else -1)
        dy = 0 if frm[1]==to[1] else (1 if to[1]>frm[1] else -1)
        x,y = frm[0]+dx, frm[1]+dy
        while (x,y)!=to:
            if board[y][x] is not None: return False
            x+=dx; y+=dy
        return True

class Bishop(Piece):
    def __init__(self, pid, color, pos=None):
        super().__init__(pid, 'bishop', color, pos)

    def can_move(self, frm, to, board):
        dx = to[0]-frm[0]; dy = to[1]-frm[1]
        if abs(dx) != abs(dy): return False
        sx = 1 if dx>0 else -1
        sy = 1 if dy>0 else -1
        x,y = frm[0]+sx, frm[1]+sy
        while (x,y)!=to:
            if board[y][x] is not None: return False
            x+=sx; y+=sy
        return True

class Queen(Piece):
    def __init__(self, pid, color, pos=None):
        super().__init__(pid, 'queen', color, pos)

    def can_move(self, frm, to, board):
        r = Rook(self.id,self.color); b = Bishop(self.id,self.color)
        return r.can_move(frm,to,board) or b.can_move(frm,to,board)

class King(Piece):
    def __init__(self, pid, color, pos=None):
        super().__init__(pid, 'king', color, pos)

    def can_move(self, frm, to, board):
        dx = abs(frm[0]-to[0]); dy = abs(frm[1]-to[1])
        return max(dx,dy) == 1

class Pawn(Piece):
    def __init__(self, pid, color, pos=None):
        super().__init__(pid, 'pawn', color, pos)

    def can_move(self, frm, to, board):
        dir = 1 if self.color=='w' else -1
        if to[0]==frm[0] and to[1]==frm[1]+dir:
            return board[to[1]][to[0]] is None
        
        if abs(to[0]-frm[0])==1 and to[1]==frm[1]+dir:
            target = board[to[1]][to[0]]
            return (target is not None) and (target.color != self.color)
        return False

class Game:
    def __init__(self):
        self.id = str(uuid.uuid4())[:8]
        self.turn = 'w'
        self.board = [[None for _ in range(8)] for _ in range(8)]
        self.pieces = {}
        self.hands = {'w': [], 'b': []}
        self.history = []
        self.first_turn_done = {'w':False,'b':False}
        self.action_done = {}

        self.init_piece()

    def init_piece(self):
        def add_piece(ptype, cnt, color):
            for i in range(cnt):
                pid = f"{color}_{ptype[0].upper()}{i}"
                piece = None
                if ptype=='pawn': piece = Pawn(pid,color)
                elif ptype=='rook': piece = Rook(pid,color)
                elif ptype=='knight': piece = Knight(pid,color)
                elif ptype=='bishop': piece = Bishop(pid,color)
                elif ptype=='queen': piece = Queen(pid,color)
                elif ptype=='king': piece = King(pid,color)
                self.pieces[pid]=piece
                self.hands[color].append(pid)

        # pawns 8
        add_piece('pawn',8,'w')
        add_piece('pawn',8,'b')
        # rooks, bishops, knights x2
        add_piece('rook',2,'w'); add_piece('rook',2,'b')
        add_piece('bishop',2,'w'); add_piece('bishop',2,'b')
        add_piece('knight',2,'w'); add_piece('knight',2,'b')
        # queen 1, king 1
        add_piece('queen',1,'w'); add_piece('queen',1,'b')
        add_piece('king',1,'w'); add_piece('king',1,'b')

    def to_json(self):
        return {
            "id": self.id,
            "turn": self.turn,
            "pieces": {pid: self.pieces[pid].to_json() for pid in self.pieces},
            "hands": self.hands,
            "history": self.history
        }

    def pos_empty(self, x,y):
        return self.board[y][x] is None

    def get_piece_at(self,x,y):
        id = self.board[y][x]
        return self.pieces[id] if id else None

    def get_piece(self, id):
        return self.pieces.get(id)

    def drop_piece(self, player_color, id, x,y):
        if not self.first_turn_done[player_color]:
            return False, "drop king first"
        if id not in self.hands[player_color]:
            return False, "you don't own that piece"
        if not (0<=x<8 and 0<=y<8): return False, "invalid coords"
        if self.board[y][x]: return False, "target occupied"
        p = self.pieces[id]
        if p.type=='pawn':
            # 폰은 각 플레이어 기준 맨 끝 랭크에 착수할 수 없다.
            if player_color=='w' and y==7: return False, "white cannot drop pawn on last rank"
            if player_color=='b' and y==0: return False, "black cannot drop pawn on first rank"
            # 폰은 착수 랭크에 따라 스턴 스택이 다르게 쌓이며, 다음과 같다.백 기준으로 랭크 1: 0스턴 스텍 ~ 랭크 7: 6스턴 스텍. 흑은 반대로 랭크 8: 0스턴 스텍 ~ 랭크 2: 6스턴 스텍이다.
            if player_color=='w':
                p.stun = y if y<=6 else 1
            else:
                p.stun = (7-y) if y>=1 else 1
        else:
            p.stun = max(1, p.stun)
        p.drop((x,y))
        self.board[y][x] = id
        self.hands[player_color].remove(id)
        self.history.append({"action":"drop","player":player_color,"piece":id,"pos":[x,y]})
        self.first_turn_done[player_color] = True
        return True, "dropped"

    def move_piece(self, player_color, id, frm, to):
        x1,y1 = frm; x2,y2 = to
        if not (0<=x1<8 and 0<=y1<8 and 0<=x2<8 and 0<=y2<8): return False,"invalid coords"
        if self.board[y1][x1] != id: return False,"source mismatch"
        piece = self.pieces[id]
        if piece.color != player_color: return False,"not your piece"
        if piece.stun > 0:
            return False, f"piece stunned. remain stun stack : {piece.stun}"
        if not piece.can_move(frm,to,self.board_pieces()):
            return False, "illegal move for piece"
        target_id = self.board[y2][x2]
        if target_id is not None:
            target = self.pieces[target_id]
            if target.color == piece.color:
                return False, "cannot capture own piece"
            piece.capture(target)
            target.pos = None; target.captured=True; target.stun=0; target.move_stack=0
            self.hands[player_color].append(target_id)
            self.board[y2][x2] = None
        # move
        self.board[y1][x1] = None
        self.board[y2][x2] = id
        piece.pos = (x2,y2)
        self.history.append({"action":"move","player":player_color,"piece":id,"from":[x1,y1],"to":[x2,y2]})
        return True, "moved"

    def board_pieces(self):
        b = [[None for _ in range(8)] for _ in range(8)]
        for y in range(8):
            for x in range(8):
                id = self.board[y][x]
                if id:
                    b[y][x] = self.pieces[id]
        return b

    def safe_after_move(self, id, frm, to):
        gcopy = copy.deepcopy(self)
        ok, msg = gcopy.move_piece(gcopy.pieces[id].color, id, frm, to)
        if not ok:
            return False
        own_color = self.pieces[id].color
        king_exists = False
        for p in gcopy.pieces.values():
            if p.type=='king' and p.color==own_color and p.pos is not None:
                king_exists = True
        return king_exists

    def end_turn(self):
        for id,p in self.pieces.items():
            p.end_turn()
        self.turn = 'b' if self.turn=='w' else 'w'
        self.action_done = {}

game = Game()

# ---------------------------
# SocketIO events
# ---------------------------
@socketio.on('connect')
def on_connect():
    sid = request.sid
    print("connect", sid)
    emit('connected', {'sid': sid})
    # send initial state
    emit('game_state', game.to_json())

@socketio.on('join_room')
def on_join(data):
    room = data.get('room','main')
    join_room(room)
    emit('joined', {'room': room}, to=request.sid)

@socketio.on('move_request')
def on_move_request(data):
    sid = request.sid
    player_sid = sid
    # client must send: {player_color, piece_id, from: [x,y], to: [x,y]}
    player_color = data.get('player_color')
    pid = data.get('piece_id')
    frm = tuple(data.get('from'))
    to = tuple(data.get('to'))

    # check turn
    if player_color != game.turn:
        emit('move_rejected', {'reason': 'not_your_turn'}, to=sid); return

    # enforce one action per turn if we track by player identity socket -> action_done keyed by player_color
    if game.action_done.get(player_color):
        emit('move_rejected', {'reason':'already_moved_this_turn'}, to=sid); return

    # basic existence
    piece = game.get_piece(pid)
    if piece is None:
        emit('move_rejected', {'reason':'no_such_piece'}, to=sid); return

    # stun/move_stack checks
    if piece.stun > 0:
        emit('move_rejected', {'reason':'stunned','stun': piece.stun}, to=sid); return
    # If you want to require move_stack>0 to allow multi-move, check here (we allow default single move)
    # legality
    if not piece.can_move(frm,to,game.board_pieces()):
        emit('move_rejected', {'reason':'illegal_move'}, to=sid); return
    # suicide check
    if not game.safe_after_move(pid, frm, to):
        emit('move_rejected', {'reason':'suicide_or_king_lost'}, to=sid); return

    ok,msg = game.move_piece(player_color, pid, frm, to)
    if not ok:
        emit('move_rejected', {'reason':msg}, to=sid); return

    # mark action done
    game.action_done[player_color] = True
    # broadcast updated state
    socketio.emit('move_accepted', {'by': player_color, 'move': {'piece':pid,'from':frm,'to':to}})
    socketio.emit('game_state', game.to_json())

@socketio.on('drop_request')
def on_drop_request(data):
    sid = request.sid
    player_color = data.get('player_color')
    pid = data.get('piece_id')
    to = tuple(data.get('to'))

    if player_color != game.turn:
        emit('drop_rejected', {'reason':'not_your_turn'}, to=sid); return
    if game.action_done.get(player_color):
        emit('drop_rejected', {'reason':'already_moved_this_turn'}, to=sid); return

    ok,msg = game.drop_piece(player_color, pid, to[0], to[1])
    if not ok:
        emit('drop_rejected', {'reason':msg}, to=sid); return

    game.action_done[player_color] = True
    socketio.emit('drop_accepted', {'by': player_color, 'piece': pid, 'to': to})
    socketio.emit('game_state', game.to_json())

@socketio.on('end_turn')
def on_end_turn():
    sid = request.sid
    # just rotate turn and update stacks
    game.end_turn()
    socketio.emit('turn_ended', {'turn': game.turn})
    socketio.emit('game_state', game.to_json())

# basic http endpoint
@app.route('/ping')
def ping():
    return {"ok": True}

if __name__ == "__main__":
    socketio.run(app, host='0.0.0.0', port=5000,debug=True)
