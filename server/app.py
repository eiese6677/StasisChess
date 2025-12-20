# server/app.py
from flask import Flask, request
from flask_socketio import SocketIO, emit, join_room
from server.ai.model import negamax_best_action, is_game_over
from server.game.core import *
import random
from server.game.ai_adapter import apply_action, get_all_actions

app = Flask(__name__)
app.config['SECRET_KEY'] = 'dev'
socketio = SocketIO(app, cors_allowed_origins="*")

# --- Game Management ---
games = {}
player_game_map = {}

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

    # 첫 턴이면 킹을 드롭
    if not game.first_turn_done.get(AI_COLOR):
        king_id = None
        for pid in game.hands[AI_COLOR]:
            if game.pieces[pid].type == 'king':
                king_id = pid
                break
        
        if king_id:
            # AI(흑)는 킹을 (4, 7)에 놓는다
            ok, msg = game.drop_piece(AI_COLOR, king_id, 4, 7)
            if ok:
                print(f"AI drops king at (4, 7)")
                game.action_done[AI_COLOR] = True
                socketio.emit('game_state', game.to_json(), to=game.id)
                game.end_turn()
                socketio.emit('turn_ended', {'turn': game.turn}, to=game.id)
                socketio.emit('game_state', game.to_json(), to=game.id)
                return
            else:
                print(f"AI failed to drop king: {msg}")
                return
        else:
            print("AI has no king to drop.")
            return

    # Use Negamax with a reasonable depth
    action = negamax_best_action(game, depth=2) 
    
    if action is None:
        print("AI has no moves or game is over.")
        return

    print(f"AI chose negamax action: {action}")

    # Apply the action
    apply_action(game, action)
    game.action_done[AI_COLOR] = True
    socketio.emit('game_state', game.to_json(), to=game.id)
    
    if is_game_over(game):
        socketio.emit('game_end', {'winner': AI_COLOR, 'loser': 'w', 'reason': 'king_capture'}, to=game.id)
        return

    # AI의 턴을 종료한다.
    game.end_turn()
    socketio.emit('turn_ended', {'turn': game.turn}, to=game.id)
    socketio.emit('game_state', game.to_json(), to=game.id)

# ---------------------------
# SocketIO events
# ---------------------------
@socketio.on('connect')
def on_connect():
    sid = request.sid
    print(f"connect {sid}")
    # For this refactoring, we create a new game for each connection.
    # A real implementation would have a lobby, game creation, and joining logic.
    game = Game()
    games[game.id] = game
    player_game_map[sid] = game.id
    join_room(game.id)
    
    emit('connected', {'sid': sid, 'game_id': game.id})
    # send initial state for the new game
    emit('game_state', game.to_json())

@socketio.on('join_game') # A new event to handle rejoining/multiple players
def on_join(data):
    sid = request.sid
    game_id = data.get('game_id')
    game = games.get(game_id)
    if game:
        player_game_map[sid] = game_id
        join_room(game.id)
        emit('joined', {'game_id': game.id}, to=sid)
        socketio.emit('game_state', game.to_json(), to=game.id)
    else:
        emit('error', {'reason': 'game_not_found'}, to=sid)

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
def on_end_turn():
    sid = request.sid
    game = get_game_for_player(sid)
    if not game:
        print(f"end_turn requested by {sid} but no game found.")
        return

    game.end_turn()
    socketio.emit('turn_ended', {'turn': game.turn}, to=game.id)
    socketio.emit('game_state', game.to_json(), to=game.id)

    # AI
    if game.turn == AI_COLOR:
        maybe_ai_move(game)

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
    game_id = player_game_map.pop(sid, None)
    if game_id:
        game = games.get(game_id)
        # Optional: Implement logic to handle player disconnection, 
        # e.g., pause game, notify other player, or clean up game if empty.
        # For now, we'll just remove the player from the map.
        pass

# basic http endpoint
@app.route('/ping')
def ping():
    return {"ok": True}

if __name__ == "__main__":
    socketio.run(app, host='0.0.0.0', port=5000,debug=True)
