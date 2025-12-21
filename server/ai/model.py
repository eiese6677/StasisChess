import math
import random
import copy
from server.game.ai_adapter import clone_game, get_all_actions, apply_action

# 기물 가치 정의
# 기물 가치 정의
PIECE_VALUES = {
    'pawn': 100,
    'knight': 320,
    'bishop': 330,
    'rook': 500,
    'queen': 900,
    'king': 30000 
}

# Piece-Square Tables (PST)
# 백색 기준 (흑색은 보드를 뒤집어서 사용)
# 중앙 제어, 기물 발전, 킹 안전 등을 고려한 테이블입니다.
pst_pawn = [
     0,  0,  0,  0,  0,  0,  0,  0,
    50, 50, 50, 50, 50, 50, 50, 50,
    10, 10, 20, 30, 30, 20, 10, 10,
     5,  5, 10, 25, 25, 10,  5,  5,
     0,  0,  0, 20, 20,  0,  0,  0,
     5, -5,-10,  0,  0,-10, -5,  5,
     5, 10, 10,-20,-20, 10, 10,  5,
     0,  0,  0,  0,  0,  0,  0,  0
]

pst_knight = [
    -50,-40,-30,-30,-30,-30,-40,-50,
    -40,-20,  0,  0,  0,  0,-20,-40,
    -30,  0, 10, 15, 15, 10,  0,-30,
    -30,  5, 15, 20, 20, 15,  5,-30,
    -30,  0, 15, 20, 20, 15,  0,-30,
    -30,  5, 10, 15, 15, 10,  5,-30,
    -40,-20,  0,  5,  5,  0,-20,-40,
    -50,-40,-30,-30,-30,-30,-40,-50
]

pst_bishop = [
    -20,-10,-10,-10,-10,-10,-10,-20,
    -10,  0,  0,  0,  0,  0,  0,-10,
    -10,  0,  5, 10, 10,  5,  0,-10,
    -10,  5,  5, 10, 10,  5,  5,-10,
    -10,  0, 10, 10, 10, 10,  0,-10,
    -10, 10, 10, 10, 10, 10, 10,-10,
    -10,  5,  0,  0,  0,  0,  5,-10,
    -20,-10,-10,-10,-10,-10,-10,-20
]

pst_rook = [
     0,  0,  0,  0,  0,  0,  0,  0,
     5, 10, 10, 10, 10, 10, 10,  5,
    -5,  0,  0,  0,  0,  0,  0, -5,
    -5,  0,  0,  0,  0,  0,  0, -5,
    -5,  0,  0,  0,  0,  0,  0, -5,
    -5,  0,  0,  0,  0,  0,  0, -5,
    -5,  0,  0,  0,  0,  0,  0, -5,
     0,  0,  0,  5,  5,  0,  0,  0
]

pst_queen = [
    -20,-10,-10, -5, -5,-10,-10,-20,
    -10,  0,  0,  0,  0,  0,  0,-10,
    -10,  0,  5,  5,  5,  5,  0,-10,
     -5,  0,  5,  5,  5,  5,  0, -5,
      0,  0,  5,  5,  5,  5,  0, -5,
    -10,  5,  5,  5,  5,  5,  0,-10,
    -10,  0,  5,  0,  0,  0,  0,-10,
    -20,-10,-10, -5, -5,-10,-10,-20
]

pst_king = [
    -30,-40,-40,-50,-50,-40,-40,-30,
    -30,-40,-40,-50,-50,-40,-40,-30,
    -30,-40,-40,-50,-50,-40,-40,-30,
    -30,-40,-40,-50,-50,-40,-40,-30,
    -20,-30,-30,-40,-40,-30,-30,-20,
    -10,-20,-20,-20,-20,-20,-20,-10,
     20, 20,  0,  0,  0,  0, 20, 20,
     20, 30, 10,  0,  0, 10, 30, 20
]

PIECE_SQUARE_TABLES = {
    'pawn': pst_pawn,
    'knight': pst_knight,
    'bishop': pst_bishop,
    'rook': pst_rook,
    'queen': pst_queen,
    'king': pst_king
}

def is_game_over(game):
    """한쪽 왕이라도 잡히면 게임이 종료되었는지 확인합니다."""
    kings_alive = {'w': False, 'b': False}
    for p in game.pieces.values():
        if p.type == 'king':
            # 킹이 보드 위에 있거나, 아직 주인의 손에 있으면(드롭 전) 생존으로 간주
            if p.pos is not None or p.id in game.hands[p.color]:
                kings_alive[p.color] = True
                
    return not (kings_alive['w'] and kings_alive['b'])

def evaluate_board(game):
    """보드 상태를 평가하여 점수를 반환합니다. 백색에게 유리하면 양수, 흑색에게 유리하면 음수입니다."""
    if is_game_over(game):
         # 죽은 왕을 체크
        kings_alive = {'w': False, 'b': False}
        for p in game.pieces.values():
            if p.type == 'king':
                if p.pos is not None or p.id in game.hands[p.color]:
                    kings_alive[p.color] = True
        
        if not kings_alive['w']: return -float('inf') # 백색 패배
        if not kings_alive['b']: return float('inf')  # 흑색 패배

    score = 0
    for piece in game.pieces.values():
        if piece.pos is not None:  # 보드 위에 있는 기물만 계산
            value = PIECE_VALUES.get(piece.type, 0)
            
            # PST 적용
            x, y = piece.pos
            pst = PIECE_SQUARE_TABLES.get(piece.type, [])
            
            if piece.color == 'w':
                # 백색: 그대로 테이블 인덱싱 (y * 8 + x)
                # y=0이 맨 윗줄이므로, 0~63 인덱스 주의. 
                # 보통 체스 엔진은 rank 1~8. 여기서는 (0,0)이 좌상단이라 가정하고 테이블 작성됨?
                # StasisChess 보드는 (0,0) 이 좌상단(Top-Left). 
                # 백색 진영이 아래쪽(y=7)이고, 위쪽(y=0)으로 공격한다고 가정하면
                # pst_pawn[0] 은 y=0... 즉 승급 지점. 
                # 일반적인 체스 PST는 0이 A1 (좌하단) 인 경우가 많음.
                # 여기서는 테이블을 Top-Left (0,0) 기준으로 시각적으로 작성했다고 가정. (pst_pawn[7~]쪽이 시작지점)
                # 하지만, pst_pawn 보면 0줄이 0점, 1줄이 50점(승급 직전? 승급선?)
                # 보통 체스 프로그램에서 배열은 0~63 flat.
                # 여기서는 (x,y) -> y*8 + x 로 매핑.
                
                # 백색은 아래(y=7)에서 위(y=0)로 간다고 가정 (일반 체스 배치)
                # PST가 위에서부터 아래로 0~7 행으료 표현되었다면,
                # 백색에게 y=0은 적진 깊숙한 곳(좋음).
                # pst_pawn[0..7] -> 0점 (이미 승급했거나 불가능?) -> 보통 승급하면 퀸이 되므로 폰 점수는 의미 없음. 
                # pst_pawn[8..15] -> 50점 (7랭크, 승급 직전)
                # ...
                # pst_pawn[56..63] -> 0점 (1랭크, 시작 지점)
                
                # 작성된 pst_pawn을 보면 
                # 0~7 index (Row 0): 0
                # 8~15 index (Row 1): 50  <-- 여기가 백색 기준 7랭크여야 함.
                # 즉, y=0 이 Top (Black Side), y=7 이 Bottom (White Side)
                # 이 코드는 y=0 일 때 index 0~7을 참조.
                pst_val = pst[y * 8 + x]
                score += (value + pst_val)
            else:
                # 흑색: 보드를 대칭으로 뒤집어서 적용
                # 흑색은 위(y=0)에서 아래(y=7)로 공격.
                # 백색 기준의 테이블을 뒤집어서 사용 (Mirroring)
                # y -> 7-y, x -> x (좌우 대칭 필요 없는 경우) 또는 x도 대칭?
                # 보통 체스는 좌우 대칭 형태이므로 x는 그대로 둬도 되지만, 퀸/킹 사이드는 다름.
                # 간단히 y만 반전 (Row Flip)
                pst_val = pst[(7 - y) * 8 + x]
                score -= (value + pst_val)
                
    return score

def negamax(game, depth, alpha, beta, color, excluded_actions=None):
    """네가맥스 알고리즘으로 최적의 수를 찾습니다."""
    
    # 게임오버 체크
    if is_game_over(game):
        return -float('inf'), None

    if depth == 0:
        perspective = 1 if color == 'w' else -1
        return evaluate_board(game) * perspective, None

    # Optimization: 
    # 일반적인 상황에서는 드롭을 나중에 고려하지만,
    # 1. 수가 거의 없을 때 (초반, 막판)
    # 2. 킹이 없을 때 (드롭해야 함)
    # 3. 특정 깊이 이상일 때
    # 드롭을 포함해야 합니다.
    
    # 일단 모든 액션을 가져오되, 드롭 포함 여부를 결정
    # Root(depth 높은 곳)에서는 드롭도 봅니다.
    # Leaf에 가까울수록(depth 낮음) 드롭을 제외하여 가지치기 효율을 높일 수 있으나,
    # "유효한 수가 없는 경우"를 방지하기 위해 
    # get_all_actions 내부에서 "이동할 기물이 없으면 드롭이라도 반환" 하는 식의 로직이 아니므로,
    # 여기서는 좀 더 보수적으로 depth > 0 이면 다 가져오도록 하거나
    # 아니면, 기본적으로 move만 가져오고, move가 없으면 drop을 가져오는 식으로 단계별 생성도 가능.
    # 하지만 간단히 depth > 1 일때만 drop을 보되,
    # 만약 move가 하나도 없다면 drop을 보도록 fallback 로직 추가.
    
    include_drops = (depth > 1)
    actions = get_all_actions(game, color, include_drops=include_drops)
    
    # 만약 액션이 없는데, 드롭을 제외해서 없는 것일 수도 있으니 다시 확인
    if not actions and not include_drops:
        actions = get_all_actions(game, color, include_drops=True)
        
    # 그래도 없으면 패배/스테일메이트
    if not actions: 
        return -float('inf'), None # 더 이상 둘 수가 없으면 패배 처리 (또는 0 스테일메이트)

    best_value = -float('inf')
    best_action = None

    for action in actions:
        if excluded_actions and action in excluded_actions:
             continue

        # 액션을 적용하여 자식 노드 게임 상태를 만듭니다.
        child_game = clone_game(game)
        success, _ = apply_action(child_game, action)
        if not success:
            continue
        child_game.end_turn() 

        # 상대방에 대한 재귀 호출
        value, _ = negamax(child_game, depth - 1, -beta, -alpha, child_game.turn)
        value = -value 

        if value > best_value:
            best_value = value
            best_action = action
        
        alpha = max(alpha, value)
        if alpha >= beta:
            break

    return best_value, best_action

def negamax_best_action(game, depth, excluded_actions=None):
    """AI의 메인 함수. 네가맥스 탐색을 시작하고 최적의 수를 반환합니다."""
    # King drop check logic logic is implicit now via get_all_actions
    
    # if game over, return None
    if is_game_over(game):
        return None
    
    # Run negamax
    val, action = negamax(game, depth, -float('inf'), float('inf'), game.turn, excluded_actions=excluded_actions)
    
    # 만약 action이 None이고 val이 -inf라면 어쩔 수 없이 지는 상황.
    # 그래도 아무거나 둬야 한다면... actions 중 첫번째라도 반환?
    # 여기서는 None 반환하여 상위에서 처리.
    return action