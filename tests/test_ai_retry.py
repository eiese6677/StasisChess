
import unittest
from unittest.mock import MagicMock, patch
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
        
        # Verify first call had empty excluded_actions (or at least check call args)
        args1, kwargs1 = mock_negamax.call_args_list[0]
        self.assertEqual(kwargs1.get('excluded_actions'), [])
        
        # Verify second call had action_invalid in excluded_actions
        args2, kwargs2 = mock_negamax.call_args_list[1]
        self.assertEqual(kwargs2.get('excluded_actions'), [action_invalid])
        
        # Verify apply_action called twice
        self.assertEqual(mock_apply.call_count, 2)
        
        # Verify game action done
        self.assertTrue(game.action_done[AI_COLOR])

if __name__ == '__main__':
    unittest.main()
