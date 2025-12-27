import copy
import uuid
class Piece:
    def __init__(self, id, type, color, pos=None):
        self.id = id
        self.type = type            # 'pawn','rook','knight','bishop','queen','king'
        self.color = color          # 'w' or 'b'
        self.pos = pos              # (x,y) or None
        self.stun = 0
        self.move_stack = 0

    def to_json(self):
        return {
            "id": self.id,
            "type": self.type,
            "color": self.color,
            "pos": list(self.pos) if self.pos is not None else None,
            "stun": self.stun,
            "move_stack": self.move_stack,
            "captured": self.pos is None
        }

    # 각 기물 클래스에서 오버라이드
    def can_move(self, frm, to, board):
        print("오버라이드 필요")
        return False

    def get_possible_moves(self, frm, board):
        return []

    def drop(self, pos):
        self.pos = pos
        self.move_stack = 0

    def capture(self, target):
        # 만약 스택이 쌓여있는 기물을 잡았을 경우, 그 스택이 잡은 기물에게 이전된다.
        self.stun += target.stun
        self.move_stack += target.move_stack
        target.color = self.color

    def end_turn(self):
        # 이동 스텍은 스턴 스텍이 턴을 넘겨서 1씩 사라질 때마다 1씩 늘어난다.
        if self.pos is None:
            return
        if self.stun > 0:
            self.stun -= 1
            self.move_stack += 1

    def clone(self):
        # Create a new instance of the same class
        new_piece = self.__class__(self.id, self.color, self.pos)
        new_piece.type = self.type
        new_piece.stun = self.stun
        new_piece.move_stack = self.move_stack
        return new_piece

class Knight(Piece):
    def __init__(self, id, color, pos=None):
        super().__init__(id, 'knight', color, pos)

    def can_move(self, frm, to, board):
        dx = abs(frm[0]-to[0]); dy = abs(frm[1]-to[1])
        return (dx==1 and dy==2) or (dx==2 and dy==1)

    def get_possible_moves(self, frm, board):
        moves = []
        x, y = frm
        deltas = [(-2, -1), (-2, 1), (-1, -2), (-1, 2),
                  (1, -2), (1, 2), (2, -1), (2, 1)]
        for dx, dy in deltas:
            nx, ny = x + dx, y + dy
            if 0 <= nx < 8 and 0 <= ny < 8:
                moves.append((nx, ny))
        return moves

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

    def get_possible_moves(self, frm, board):
        moves = []
        x, y = frm
        directions = [(0, 1), (0, -1), (1, 0), (-1, 0)]
        for dx, dy in directions:
            nx, ny = x + dx, y + dy
            while 0 <= nx < 8 and 0 <= ny < 8:
                if board[ny][nx] is not None:
                    if board[ny][nx].color != self.color:
                        moves.append((nx, ny))
                    break
                moves.append((nx, ny))
                nx += dx
                ny += dy
        return moves

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

    def get_possible_moves(self, frm, board):
        moves = []
        x, y = frm
        directions = [(1, 1), (1, -1), (-1, 1), (-1, -1)]
        for dx, dy in directions:
            nx, ny = x + dx, y + dy
            while 0 <= nx < 8 and 0 <= ny < 8:
                if board[ny][nx] is not None:
                    if board[ny][nx].color != self.color:
                        moves.append((nx, ny))
                    break
                moves.append((nx, ny))
                nx += dx
                ny += dy
        return moves

class Queen(Piece):
    def __init__(self, pid, color, pos=None):
        super().__init__(pid, 'queen', color, pos)

    def can_move(self, frm, to, board):
        r = Rook('temp',self.color); b = Bishop('temp',self.color)
        return r.can_move(frm,to,board) or b.can_move(frm,to,board)

    def get_possible_moves(self, frm, board):
        r = Rook('temp', self.color)
        b = Bishop('temp', self.color)
        return r.get_possible_moves(frm, board) + b.get_possible_moves(frm, board)

class King(Piece):
    def __init__(self, pid, color, pos=None):
        super().__init__(pid, 'king', color, pos)

    def can_move(self, frm, to, board):
        dx = abs(frm[0]-to[0]); dy = abs(frm[1]-to[1])
        return max(dx,dy) == 1

    def get_possible_moves(self, frm, board):
        moves = []
        x, y = frm
        for dx in [-1, 0, 1]:
            for dy in [-1, 0, 1]:
                if dx == 0 and dy == 0:
                    continue
                nx, ny = x + dx, y + dy
                if 0 <= nx < 8 and 0 <= ny < 8:
                    moves.append((nx, ny))
        return moves

class Pawn(Piece):
    def __init__(self, pid, color, pos=None):
        super().__init__(pid, 'pawn', color, pos)

    def can_move(self, frm, to, board):
        dir = 1 if self.color=='b' else -1
        if to[0]==frm[0] and to[1]==frm[1]+dir:
            return board[to[1]][to[0]] is None
        
        if abs(to[0]-frm[0])==1 and to[1]==frm[1]+dir:
            target = board[to[1]][to[0]]
            return (target is not None) and (target.color != self.color)
        return False

    def get_possible_moves(self, frm, board):
        moves = []
        x, y = frm
        dir = 1 if self.color == 'b' else -1

        # Forward move
        if 0 <= y + dir < 8 and board[y + dir][x] is None:
            moves.append((x, y + dir))

        # Capture moves
        for dx in [-1, 1]:
            if 0 <= x + dx < 8 and 0 <= y + dir < 8:
                target = board[y + dir][x + dx]
                if target is not None and target.color != self.color:
                    moves.append((x + dx, y + dir))
        return moves

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
        self.dropped = False

        self.init_piece()

    def fast_clone(self):
        new_game = Game.__new__(Game) # Skip init
        new_game.id = self.id
        new_game.turn = self.turn
        
        # Optimize: reuse immutable pieces if possible, or use fast shallow copy?
        # Since pieces are mutable (pos, stun), we must copy them.
        # But copy.copy is faster than class instantiation
        new_game.pieces = {}
        for pid, p in self.pieces.items():
            new_game.pieces[pid] = copy.copy(p)
            
        # Optimize: Copy board directly instead of rebuilding
        # self.board is list of lists of strings (immutable)
        new_game.board = [row[:] for row in self.board]
                
        # Copy hands (list of strings)
        new_game.hands = {'w': self.hands['w'][:], 'b': self.hands['b'][:]}
        
        # Skip history for AI
        new_game.history = [] 
        
        new_game.first_turn_done = self.first_turn_done.copy()
        new_game.action_done = self.action_done.copy()
        
        return new_game

    def init_piece(self):
        def add_piece(ptype, cnt, color):
            for i in range(cnt):
                abbr = ptype[0].upper()
                if ptype == 'knight':
                    abbr = 'N'
                pid = f"{color}_{abbr}{i}"
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
        try:
            if self.dropped:
                return False, "already dropped"
        except AttributeError:
            self.dropped = True
        if id not in self.hands[player_color]:
            return False, "you don't own that piece"
        p = self.pieces[id]
        if not self.first_turn_done[player_color] and p.type != 'king':
            return False, "drop king first"
        if not (0<=x<8 and 0<=y<8): return False, "invalid coords"
        if self.board[y][x]: return False, "target occupied"
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
        self.dropped = True
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
        is_win = False
        if target_id is not None:
            target = self.pieces[target_id]
            if target.color == piece.color:
                return False, "cannot capture own piece"
            
            # Check for win condition (king capture)
            if target.type == 'king':
                is_win = True

            piece.capture(target)
            target.pos = None; target.stun=0; target.move_stack=0
            self.hands[player_color].append(target_id)
            self.board[y2][x2] = None
        
        # move
        self.board[y1][x1] = None
        self.board[y2][x2] = id
        piece.pos = (x2,y2)
        piece.move_stack -= 1
        
        self.history.append({"action":"move","player":player_color,"piece":id,"from":[x1,y1],"to":[x2,y2]})

        if is_win:
            return True, "win"
        
        return True, "moved"

    def board_pieces(self):
        b = [[None for _ in range(8)] for _ in range(8)]
        for y in range(8):
            for x in range(8):
                id = self.board[y][x]
                if id:
                    b[y][x] = self.pieces[id]
        return b

    def safe_after_move(self, id, frm, to,color):
        gcopy = self.fast_clone()
        ok, msg = gcopy.move_piece(gcopy.pieces[id].color, id, frm, to)
        if not ok:
            return False
        king_exists = False
        for p in gcopy.pieces.values():
            if p.type=='king' and p.color==color and p.pos is not None:
                king_exists = True
        return king_exists

    def get_legal_moves(self, piece_id):
        piece = self.get_piece(piece_id)
        if not piece:
            return []

        if piece.pos is None:
            return []

    def get_legal_moves(self, piece_id):
        piece = self.get_piece(piece_id)
        if not piece:
            return []

        if piece.pos is None:
            return []

        if piece.stun > 0 or piece.move_stack < 1:
            return []

        legal_moves = []
        frm = piece.pos
        possible_moves = piece.get_possible_moves(frm, self.board_pieces())
        
        for to in possible_moves:
            target_piece = self.get_piece_at(to[0], to[1])
            if target_piece and target_piece.color == piece.color:
                continue

            if self.safe_after_move(piece_id, frm, to, piece.color):
                legal_moves.append(to)
        
        return legal_moves

    def get_pseudo_legal_moves(self, piece_id):
        # Similar to get_legal_moves but SKIPS safe_after_move check
        piece = self.get_piece(piece_id)
        if not piece:
            return []
        if piece.pos is None:
            return []
        if piece.stun > 0 or piece.move_stack < 1:
            return []

        moves = []
        frm = piece.pos
        possible_moves = piece.get_possible_moves(frm, self.board_pieces())
        
        for to in possible_moves:
            target_piece = self.get_piece_at(to[0], to[1])
            if target_piece and target_piece.color == piece.color:
                continue
            moves.append(to)
        return moves

    def end_turn(self):
        for id,p in self.pieces.items():
            p.end_turn()
        self.turn = 'b' if self.turn=='w' else 'w'
        self.action_done = {}
        self.dropped = False

def can_p(game):
    b = game.board
    ls = []
    # Iterate over valid board coordinates (y, x)
    for y in range(8):
        for x in range(8):
            pid = b[y][x]
            # Skip empty squares
            if pid is None:
                continue
            if game.pieces[pid].type == 'pawn':
                # Return coordinates as (x, y) to match other APIs
                ls.append((x, y))
    return ls