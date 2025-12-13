// client/src/App.jsx
import { useGame } from "./hooks/useGame";
import Board from "./components/Board";
import Hand from "./components/Hand";

const styles = {
  root: { position: 'relative', padding: 20, display: 'flex', gap: '20px' },
  gameArea: { display: 'flex', flexDirection: 'column', gap: '10px' },
  turnInfo: { marginTop: 10 },
  sideBar: { display: 'flex', flexDirection: 'column', gap: '20px' },
  log: { whiteSpace: 'pre-wrap', maxHeight: 300, overflow: 'auto', border: '1px solid #ccc', padding: 5 },
  gameOverOverlay: {
    position: 'absolute',
    top: 0,
    left: 0,
    right: 0,
    bottom: 0,
    backgroundColor: 'rgba(0,0,0,0.7)',
    color: 'white',
    display: 'flex',
    justifyContent: 'center',
    alignItems: 'center',
    fontSize: '3em',
    zIndex: 100,
  }
};

export default function App() {
  const { gameState, log, selectedPiece, gameId, gameOver, winner, handleSelect, handleSelectFromHand, endTurn } = useGame();

  if (!gameState) {
    return <div>Loading...</div>;
  }

  return (
    <div style={styles.root}>
      {gameOver && (
        <div style={styles.gameOverOverlay}>
          <span>Game Over! {winner === 'w' ? 'White' : 'Black'} wins!</span>
        </div>
      )}
      <div style={styles.gameArea}>
        <h2>Stasis Chess</h2>
        <p>Game ID: {gameId}</p>
        <Board pieces={gameState.pieces} onSelect={handleSelect} selectedPiece={selectedPiece} />
        <div style={styles.turnInfo}>
          <h3>Turn: {gameState.turn === 'w' ? 'White' : 'Black'}</h3>
          <button onClick={endTurn}>End Turn</button>
        </div>
      </div>
      <div style={styles.sideBar}>
        <Hand color="w" pieces={gameState.pieces} hands={gameState.hands} onSelect={handleSelectFromHand} selectedPiece={selectedPiece} />
        <Hand color="b" pieces={gameState.pieces} hands={gameState.hands} onSelect={handleSelectFromHand} selectedPiece={selectedPiece} />
        <h3>Log</h3>
        <div style={styles.log}>
          {log.map((l, i) => (<div key={i}>{l}</div>))}
        </div>
      </div>
    </div>
  );
}