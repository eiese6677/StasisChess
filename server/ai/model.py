import math
import random
import copy
from server.game.ai_adapter import clone_game, get_all_actions, apply_action

# 기물 가치 정의
PIECE_VALUES = {
    'pawn': 1,
    'knight': 3,
    'bishop': 3,
    'rook': 5,
    'queen': 9,
    'king': 1000  # 왕의 가치는 매우 높게 설정 (실제로는 승패를 결정)
}

def is_game_over(game):
    """한쪽 왕이라도 잡히면 게임이 종료되었는지 확인합니다."""
    kings = {'w': False, 'b': False}
    for p in game.pieces.values():
        if p.type == 'king' and p.pos is not None:
            kings[p.color] = True
    return not (kings['w'] and kings['b'])

def evaluate_board(game):
    """보드 상태를 평가하여 점수를 반환합니다. 백색에게 유리하면 양수, 흑색에게 유리하면 음수입니다."""
    score = 0
    for piece in game.pieces.values():
        if piece.pos is not None:  # 보드 위에 있는 기물만 계산
            value = PIECE_VALUES.get(piece.type, 0)
            if piece.color == 'w':
                score += value
            else:
                score -= value
    return score

def negamax(game, depth, alpha, beta, color, excluded_actions=None):
    """네가맥스 알고리즘으로 최적의 수를 찾습니다."""
    
    # 게임이 끝났거나 깊이가 0에 도달하면, 현재 플레이어 관점의 평가 점수를 반환합니다.
    if is_game_over(game):
        # 현재 턴의 플레이어가 졌으므로 매우 낮은 점수를 반환합니다.
        return -PIECE_VALUES['king'], None
        
    if depth == 0:
        perspective = 1 if color == 'w' else -1
        return evaluate_board(game) * perspective, None

    best_value = -float('inf')
    best_action = None
    
    # Optimization: Only consider drops at higher depths (Root) to reduce branching factor.
    # If depth=1 (Leaf node checking opponent reply), ignore drops.
    include_drops = (depth > 1) 
    actions = get_all_actions(game, color, include_drops=include_drops)
    if not actions: # 움직일 수 있는 수가 없음 (스테일메이트)
        return 0, None

    for action in actions:
        if excluded_actions and action in excluded_actions:
             continue

        # 액션을 적용하여 자식 노드 게임 상태를 만듭니다.
        child_game = clone_game(game)
        success, _ = apply_action(child_game, action)
        if not success:
            continue
        child_game.end_turn() # 시뮬레이션에서 턴을 넘깁니다.

        # 상대방에 대한 재귀 호출
        value, _ = negamax(child_game, depth - 1, -beta, -alpha, child_game.turn)
        value = -value # 상대방의 점수를 내 관점으로 변환합니다.

        if value > best_value:
            best_value = value
            best_action = action
        
        alpha = max(alpha, value)
        if alpha >= beta:
            break  # 알파-베타 가지치기

    return best_value, best_action

def negamax_best_action(game, depth, excluded_actions=None):
    """AI의 메인 함수. 네가맥스 탐색을 시작하고 최적의 수를 반환합니다."""
    if is_game_over(game):
        return None
    
    _, action = negamax(game, depth, -float('inf'), float('inf'), game.turn, excluded_actions=excluded_actions)
    return action