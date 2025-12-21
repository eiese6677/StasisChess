
import unittest
from unittest.mock import MagicMock, patch
import sys
import types

# Provide minimal stubs for optional dependencies so tests can run in minimal env
if 'flask' not in sys.modules:
    fake_flask = types.ModuleType('flask')
    class DummyFlask:
        def __init__(self, *args, **kwargs):
            self.config = {}
        def route(self, *args, **kwargs):
            def deco(f):
                return f
            return deco
    fake_flask.Flask = DummyFlask
    fake_flask.request = types.SimpleNamespace(sid=None)
    sys.modules['flask'] = fake_flask

if 'flask_socketio' not in sys.modules:
    fake_socketio = types.ModuleType('flask_socketio')
    class DummySocketIO:
        def __init__(self, *args, **kwargs):
            pass
        def on(self, event):
            def deco(f):
                return f
            return deco
        def emit(self, *a, **k):
            pass
    fake_socketio.SocketIO = DummySocketIO
    fake_socketio.emit = lambda *a, **k: None
    fake_socketio.join_room = lambda *a, **k: None
    sys.modules['flask_socketio'] = fake_socketio

from server.app import maybe_ai_move, AI_COLOR
from server.game.core import Game

class TestAIRetry(unittest.TestCase):
    @patch('server.app.negamax_best_action')
    @patch('server.app.apply_action')
    @patch('server.app.socketio')
    def test_retry_on_failure(self, mock_socketio, mock_apply, mock_negamax):
        game = Game()
        game.turn = AI_COLOR
        game.first_turn_done[AI_COLOR] = True # Skip king drop
        
        # Determine strict strict order of return values
        # 1. Invalid Action -> apply_action returns False
        # 2. Valid Action -> apply_action returns True
        
        action_invalid = ("move", "b_p0", (0,1), (0,2))
        action_valid = ("move", "b_p1", (1,1), (1,2))
        
        mock_negamax.side_effect = [action_invalid, action_valid]
        mock_apply.side_effect = [(False, "invalid move"), (True, "ok")]
        
        try:
            maybe_ai_move(game)
        except Exception as e:
            self.fail(f"maybe_ai_move raised exception: {e}")
            
        # Verify negamax was called twice
        self.assertEqual(mock_negamax.call_count, 2)
        
        # Verify first call had empty excluded_actions (Cannot verify strict equality due to mutable reference in mock)
        args1, kwargs1 = mock_negamax.call_args_list[0]
        # self.assertEqual(kwargs1.get('excluded_actions'), []) 
        
        # Verify second call had action_invalid in excluded_actions
        args2, kwargs2 = mock_negamax.call_args_list[1]
        self.assertEqual(kwargs2.get('excluded_actions'), [action_invalid])
        
        # Verify apply_action called twice
        self.assertEqual(mock_apply.call_count, 2)
        
        # Verify game action done (actually end_turn clears it, so check turn flipped)
        # self.assertTrue(game.action_done[AI_COLOR])
        self.assertNotEqual(game.turn, AI_COLOR)

if __name__ == '__main__':
    unittest.main()
