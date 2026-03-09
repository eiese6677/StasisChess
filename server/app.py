# server/app.py
from flask import Flask, request, send_from_directory, jsonify
from flask_socketio import SocketIO, emit, join_room
from server.ai.model import negamax_best_action, is_game_over
from server.game.core import *
import random
from server.game.ai_adapter import apply_action, get_all_actions
import os
import uuid

# Get the parent directory (project root)
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

app = Flask(__name__, static_folder=os.path.join(project_root, 'dist'), static_url_path='/')
app.config['SECRET_KEY'] = 'dev'
socketio = SocketIO(app, cors_allowed_origins="*")

# --- Game Management ---
games = {}
player_game_map = {}
player_color_map = {}  # 각 플레이어의 색 저장

# --- Room Management ---
rooms = {}  # room_id -> room_info
player_room_map = {}  # sid -> room_id

def create_room(name, creator_sid):
    room_id = str(uuid.uuid4())[:8]
    room = {
        'id': room_id,
        'name': name,
        'status': 'waiting',  # waiting, playing, finished
        'players': [creator_sid],
        'game_id': None,
        'created_at': os.times()[4] if hasattr(os, 'times') else 0
    }
    rooms[room_id] = room
    player_room_map[creator_sid] = room_id
    return room

def get_room_list():
    return [{
        'id': room['id'],
        'name': room['name'],
        'status': room['status'],
        'player_count': len(room['players']),
        'max_players': 2
    } for room in rooms.values() if room['status'] != 'finished']
waiting_room = []      # 게임을 기다리는 플레이어들

def get_game_for_player(sid):
    game_id = player_game_map.get(sid)
    if game_id:
        return games.get(game_id)
    return None

# ----------- AI ------------
AI_COLOR = 'b'   # 흑을 AI로

def maybe_ai_move(game):
    if game.turn != AI_COLOR:
        return

    # Use Negamax with a reasonable depth
    # First turn (King drop) is now handled by generalized negamax
    excluded_actions = []
    max_retries = 10000000

    for _ in range(max_retries):
        action = negamax_best_action(game, depth=2, excluded_actions=excluded_actions)
        
        if action is None:
            print("AI has no moves or game is over.")
            return
    
        print(f"AI chose negamax action: {action}")
    
        # Apply the action
        success, msg = apply_action(game, action)
        if success:
            game.action_done[AI_COLOR] = True
            socketio.emit('game_state', game.to_json(), to=game.id)
            
            if is_game_over(game):
                socketio.emit('game_end', {'winner': AI_COLOR, 'loser': 'w', 'reason': 'king_capture'}, to=game.id)
                return
            break # Success, exit loop
        else:
            print(f"AI move failed: {msg}. Retrying...")
            excluded_actions.append(action)
    else:
        print("AI failed to find valid move after max retries")
        return

    # AI의 턴을 종료한다.
    game.end_turn('b')
    socketio.emit('turn_ended', {'turn': game.turn}, to=game.id)
    socketio.emit('game_state', game.to_json(), to=game.id)

# ---------------------------
# SocketIO events
# ---------------------------
@socketio.on('connect')
def on_connect():
    sid = request.sid
    print(f"connect {sid}")
    # 연결만 확인하고 대기
    

@socketio.on('join_game')
def on_join(data):
    sid = request.sid
    game_id = data.get('game_id')
    print(f"join_game 이벤트 수신: sid={sid}, game_id={game_id}")
    game = games.get(game_id)
    if game:
        join_room(game_id)
        player_color = player_color_map.get(sid)
        print(f"게임 참가 성공: sid={sid}, color={player_color}, game_id={game_id}")
        socketio.emit('joined', {
            'game_id': game_id,
            'player_color': player_color
        }, to=sid)
        
        # 모든 플레이어에게 게임 상태 전송
        socketio.emit('game_state', game.to_json(), to=game_id)
        print(f"game_state 전송: game_id={game_id}")
        print(f"플레이어 {sid}({player_color})가 게임 {game_id}에 입장했습니다")
    else:
        print(f"게임 참가 실패: 게임을 찾을 수 없음 game_id={game_id}")
        socketio.emit('error', {'reason': 'game_not_found'}, to=sid)

@socketio.on('move_request')
def on_move_request(data):
    sid = request.sid
    game = get_game_for_player(sid)
    if not game:
        emit('move_rejected', {'reason': 'game_not_found'}, to=sid); return
        
    player_color = data.get('player_color')
    pid = data.get('piece_id')
    frm = tuple(data.get('from'))
    to = tuple(data.get('to'))

    # check turn
    if player_color != game.turn:
        emit('move_rejected', {'reason': 'not_your_turn'}, to=sid); return

    if game.action_done.get(player_color):
        emit('move_rejected', {'reason':'already_moved_this_turn'}, to=sid); return

    piece = game.get_piece(pid)
    if piece is None:
        emit('move_rejected', {'reason':'no_such_piece'}, to=sid); return

    if piece.stun > 0:
        emit('move_rejected', {'reason':'stunned','stun': piece.stun}, to=sid); return
    
    if piece.move_stack < 1:
        emit('move_rejected', {'reason':'move_stack_is_0'}); return
    
    if not piece.can_move(frm,to,game.board_pieces()):
        emit('move_rejected', {'reason':'illegal_move'}, to=sid); return
    
    if not game.safe_after_move(pid, frm, to,piece.color):
        emit('move_rejected', {'reason':'suicide_or_king_lost'}, to=sid); return

    ok,msg = game.move_piece(player_color, pid, frm, to)
    if not ok:
        emit('move_rejected', {'reason':msg}, to=sid); return
    
    print(to[1])
    print(piece.type)
    if to[1] in (0, 7) and piece.type == "pawn":
        # Promote pawn to a Queen instance (preserve id, color, pos)
        x, y = to
        promoted = Queen(pid, piece.color, pos=(x, y))
        promoted.stun = 0
        promoted.move_stack = 5
        # Replace the piece object in the game with the promoted queen
        game.pieces[pid] = promoted
        # Ensure board entry remains consistent
        game.board[y][x] = pid
        print(f"Pawn {pid} promoted to Queen at {(x,y)}")
        
    game.action_done[player_color] = True
    socketio.emit('move_accepted', {'by': player_color, 'move': {'piece':pid,'from':frm,'to':to}}, to=game.id)
    socketio.emit('game_state', game.to_json(), to=game.id)
    if msg == "win":
        winner = player_color
        loser = 'b' if player_color == 'w' else 'w'
        socketio.emit('game_end', {'winner': winner, 'loser': loser, 'reason': 'king_capture'}, to=game.id)
        return

@socketio.on('drop_request')
def on_drop_request(data):
    sid = request.sid
    game = get_game_for_player(sid)
    if not game:
        emit('drop_rejected', {'reason': 'game_not_found'}, to=sid); return

    player_color = data.get('player_color')
    pid = data.get('piece_id')
    to = tuple(data.get('to'))

    if player_color != game.turn:
        emit('drop_rejected', {'reason':'not_your_turn'}, to=sid); return
    
    ok,msg = game.drop_piece(player_color, pid, to[0], to[1])
    if not ok:
        emit('drop_rejected', {'reason':msg}, to=sid); return

    game.action_done[player_color] = True
    socketio.emit('drop_accepted', {'by': player_color, 'piece': pid, 'to': to}, to=game.id)
    socketio.emit('game_state', game.to_json(), to=game.id)

@socketio.on('end_turn')
def on_end_turn(player_color):
    sid = request.sid
    game = get_game_for_player(sid)
    if not game:
        print(f"end_turn requested by {sid} but no game found.")
        return

    game.end_turn(player_color)
    socketio.emit('turn_ended', {'turn': game.turn}, to=game.id)
    socketio.emit('game_state', game.to_json(), to=game.id)

@socketio.on('stack_add')
def on_stack_add(data):
    sid = request.sid
    game = get_game_for_player(sid)
    if not game:
        emit('stack_rejected', {'reason': 'game_not_found'}, to=sid); return
    id = data.get('piece_id')
    p = game.get_piece(id)
    if game.action_done.get(p.color):
        emit('stack_rejected', {'reason':'already_moved_this_turn'}, to=sid); return
    if p.type=='king':
        emit('stack_rejected', {'reason':'can_not_add_stun_king'}, to=sid); return
    p.stun += 1
    game.action_done[p.color] = True
    socketio.emit('game_state', game.to_json(), to=game.id)

@socketio.on('get_legal_moves')
def on_get_legal_moves(data):
    sid = request.sid
    game = get_game_for_player(sid)
    if not game:
        return

    piece_id = data.get('piece_id')
    if not piece_id:
        return

    moves = game.get_legal_moves(piece_id)
    emit('legal_moves', {'moves': moves}, to=sid)

@socketio.on('disconnect')
def on_disconnect():
    sid = request.sid
    print(f"disconnect {sid}")
    
    # 방에서 나가기
    room_id = player_room_map.pop(sid, None)
    if room_id:
        room = rooms.get(room_id)
        if room and sid in room['players']:
            room['players'].remove(sid)
            
            # 방에 플레이어가 없으면 방 삭제
            if not room['players']:
                rooms.pop(room_id, None)
                print(f"방 {room_id}가 비어 삭제되었습니다")
            else:
                # 다른 플레이어에게 알림
                socketio.emit('player_left', {
                    'message': '상대방이 방을 나갔습니다.',
                    'room_id': room_id
                }, to=room_id)
    
    # 게임 중이었으면
    game_id = player_game_map.pop(sid, None)
    if game_id:
        game = games.get(game_id)
        player_color = player_color_map.pop(sid, None)
        
        if game:
            # 상대방에게 플레이어 나감을 알림
            socketio.emit('opponent_disconnected', {
                'disconnected_color': player_color,
                'message': '상대방이 연결을 끊었습니다.'
            }, to=game_id)
            
            # 게임 정리
            games.pop(game_id, None)
            
            # 다른 플레이어도 매핑 제거
            for other_sid, gid in list(player_game_map.items()):
                if gid == game_id:
                    player_game_map.pop(other_sid, None)
                    player_color_map.pop(other_sid, None)

# basic http endpoint
@app.route('/ping')
def ping():
    return {"ok": True}

# --- Room API ---
@app.route('/api/rooms', methods=['GET'])
def get_rooms():
    """방 목록 조회"""
    room_list = get_room_list()
    return jsonify({'rooms': room_list})

@app.route('/api/rooms', methods=['POST'])
def create_room_api():
    """방 생성"""
    data = request.get_json()
    room_name = data.get('name', '새로운 게임')
    creator_sid = data.get('sid')
    
    if not creator_sid:
        return jsonify({'error': 'sid is required'}), 400
    
    room = create_room(room_name, creator_sid)
    print(f"방 생성: {room['id']} - {room['name']}")
    
    return jsonify({
        'room': {
            'id': room['id'],
            'name': room['name'],
            'status': room['status']
        }
    })

@app.route('/api/rooms/<room_id>/join', methods=['POST'])
def join_room_api(room_id):
    """방 참가"""
    data = request.get_json()
    player_sid = data.get('sid')
    
    if not player_sid:
        return jsonify({'error': 'sid is required'}), 400
    
    room = rooms.get(room_id)
    if not room:
        return jsonify({'error': 'room not found'}), 404
    
    if room['status'] != 'waiting':
        return jsonify({'error': 'room is not available'}), 400
    
    if len(room['players']) >= 2:
        return jsonify({'error': 'room is full'}), 400
    
    if player_sid in room['players']:
        return jsonify({'error': 'already in room'}), 400
    
    # 플레이어 추가
    room['players'].append(player_sid)
    player_room_map[player_sid] = room_id
    
    print(f"플레이어 {player_sid}가 방 {room_id}에 참가했습니다")
    
    # 2명이 모였으면 게임 시작
    if len(room['players']) == 2:
        start_game_for_room(room_id)
    
    return jsonify({
        'room': {
            'id': room['id'],
            'name': room['name'],
            'status': room['status'],
            'player_count': len(room['players'])
        }
    })

def start_game_for_room(room_id):
    """방의 게임 시작"""
    room = rooms.get(room_id)
    if not room or len(room['players']) != 2:
        return
    
    player1_sid = room['players'][0]
    player2_sid = room['players'][1]
    
    # 게임 생성
    game = Game()
    games[game.id] = game
    room['game_id'] = game.id
    room['status'] = 'playing'
    
    # 플레이어 매핑
    player_game_map[player1_sid] = game.id
    player_game_map[player2_sid] = game.id
    player_color_map[player1_sid] = 'w'  # 흰색
    player_color_map[player2_sid] = 'b'  # 검은색
    
    # Socket.IO로 게임 시작 알림
    socketio.emit('game_ready', {
        'game_id': game.id,
        'player_color': 'w',
        'room_id': room_id
    }, to=player1_sid)
    
    socketio.emit('game_ready', {
        'game_id': game.id,
        'player_color': 'b',
        'room_id': room_id
    }, to=player2_sid)
    
    print(f"방 {room_id}의 게임 {game.id} 시작. 플레이어1(흰색): {player1_sid}, 플레이어2(검은색): {player2_sid}")
    print(f"game_ready 이벤트 전송: player1={player1_sid}, player2={player2_sid}")

@app.route('/')
def main():
    dist_path = os.path.join(project_root, 'dist')
    return send_from_directory(dist_path, 'index.html')

if __name__ == "__main__":
    socketio.run(app, host='0.0.0.0', port=5000,debug=True)
