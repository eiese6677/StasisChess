// client/src/App.jsx
import { useState, useEffect } from "react";
import { io } from 'socket.io-client';
import { useGame } from "./hooks/useGame";
import Board from "./components/Board";
import Hand from "./components/Hand";
import Lobby from "./components/Lobby";

const socket = io("http://127.0.0.1:5000");

const styles = {
  root: { position: 'relative', display: 'flex', gap: '20px', zoom: '95%' },
  gameArea: { display: 'flex', flexDirection: 'column', gap: '10px' },
  turnInfo: { marginTop: 10, display: 'flex', alignItems: 'center', gap: '10px' },
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
  },
  lobby: {
    maxWidth: '800px',
    margin: '0 auto',
    padding: '20px',
    fontFamily: 'Arial, sans-serif'
  },
  roomList: {
    display: 'grid',
    gap: '10px',
    marginBottom: '20px'
  },
  roomItem: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    padding: '15px',
    border: '1px solid #ddd',
    borderRadius: '5px',
    backgroundColor: '#f9f9f9'
  },
  roomButton: {
    padding: '8px 16px',
    backgroundColor: '#007bff',
    color: 'white',
    border: 'none',
    borderRadius: '4px',
    cursor: 'pointer'
  },
  createRoom: {
    marginBottom: '20px',
    padding: '15px',
    border: '1px solid #ddd',
    borderRadius: '5px',
    backgroundColor: '#f0f8ff'
  },
  input: {
    padding: '8px',
    marginRight: '10px',
    border: '1px solid #ccc',
    borderRadius: '4px'
  }
};

export default function App() {
  const [currentView, setCurrentView] = useState('lobby'); // 'lobby', 'loading' or 'game'
  const [playerSid, setPlayerSid] = useState(null);
  const [socketConnected, setSocketConnected] = useState(false);
  const [showLog, setShowLog] = useState(false);

  // URL 파라미터에서 게임/방 ID 확인
  const [urlParams] = useState(() => new URLSearchParams(window.location.search));
  const gameIdFromUrl = urlParams.get('game_id');
  const roomIdFromUrl = urlParams.get('room_id');

  const {
    gameState,
    log,
    selectedPiece,
    confirmedPiece,
    legalMoves,
    gameId,
    gameOver,
    winner,
    handleSelect,
    handleSelectFromHand,
    endTurn,
    toggleConfirmSelection
  } = useGame(socket, (gameEndData) => {
    // 게임 종료 시 로비로 돌아가고 URL 초기화
    setTimeout(() => {
      setCurrentView('lobby');
      window.history.pushState({}, '', window.location.pathname);
    }, 3000); // 3초 후 자동으로 로비로 돌아감
  });

  useEffect(() => {
    // Socket.IO 연결
    socket.on('connect', () => {
      console.log('Socket.IO 연결됨');
      setPlayerSid(socket.id);
      setSocketConnected(true);
    });

    socket.on('disconnect', () => {
      console.log('Socket.IO 연결 끊어짐');
      setSocketConnected(false);
      setPlayerSid(null);
    });

    socket.on('player_left', (data) => {
      alert(data.message);
      setCurrentView('lobby');
    });

    socket.on('opponent_disconnected', (data) => {
      alert(data.message);
      setCurrentView('lobby');
      // URL 초기화
      window.history.pushState({}, '', window.location.pathname);
    });

    return () => {
      socket.off('connect');
      socket.off('disconnect');
      socket.off('player_left');
      socket.off('opponent_disconnected');
    };
  }, []);

  // gameState가 로드되면 게임 화면으로 전환
  useEffect(() => {
    if (gameState && currentView === 'loading') {
      console.log('gameState 로드됨, 게임 화면으로 전환');
      setCurrentView('game');
    }
  }, [gameState, currentView]);

  // URL 파라미터로 게임 자동 참가
  useEffect(() => {
    if (playerSid && gameIdFromUrl && currentView === 'lobby') {
      console.log('URL에서 게임 ID 발견, 자동 참가:', gameIdFromUrl);
      socket.emit('join_game', { game_id: gameIdFromUrl });
      setCurrentView('loading'); // 로딩 화면으로 전환
    }
  }, [playerSid, gameIdFromUrl, currentView]);

  // 로비 화면
  if (currentView === 'lobby') {
    return (
      <Lobby
        playerSid={playerSid}
        socket={socket}
        onGameReady={(data) => {
          console.log('onGameReady 콜백 - game_id:', data.game_id);
          // URL 업데이트
          const newUrl = `${window.location.pathname}?game_id=${data.game_id}`;
          window.history.pushState({}, '', newUrl);
          // 서버에 join_game 이벤트 전송
          socket.emit('join_game', { game_id: data.game_id });
          setCurrentView('loading');
        }}
      />
    );
  }

  // 로딩 화면
  if (currentView === 'loading') {
    return (
      <div style={{ padding: '20px', textAlign: 'center' }}>
        <h2>Loading game...</h2>
        <p>게임 상태를 기다리는 중입니다.</p>
        <p>게임 ID: {gameId || '없음'}</p>
        <p>현재 뷰: {currentView}</p>
        <p>플레이어 SID: {playerSid || '연결 안됨'}</p>
        <p>Socket.IO: {socketConnected ? '연결됨' : '연결 안됨'}</p>
        <p>URL 게임 ID: {gameIdFromUrl || '없음'}</p>
        <div style={{ marginTop: '20px' }}>
          {!socketConnected && (
            <button
              style={styles.roomButton}
              onClick={() => {
                console.log('Socket.IO 재연결 시도');
                socket.connect();
              }}
            >
              Socket.IO 재연결
            </button>
          )}
          {gameIdFromUrl && socketConnected && (
            <button
              style={styles.roomButton}
              onClick={() => {
                console.log('수동 join_game 전송:', gameIdFromUrl);
                socket.emit('join_game', { game_id: gameIdFromUrl });
              }}
            >
              수동 참가 시도
            </button>
          )}
          <button
            style={{ ...styles.roomButton, backgroundColor: '#dc3545', marginLeft: '10px' }}
            onClick={() => {
              setCurrentView('lobby');
              window.location.href = window.location.pathname; // 완전 새로고침
            }}
          >
            로비로 돌아가기 (새로고침)
          </button>
        </div>
      </div>
    );
  }

  // 게임 화면
  if (currentView === 'game') {
    if (!gameState) {
      // 게임 뷰지만 gameState가 없는 경우 로딩으로 전환
      setCurrentView('loading');
      return null;
    }

    console.log('게임 화면 렌더링 - gameState:', gameState);

    return (
      <div style={styles.root}>
        {gameOver && (
          <div style={styles.gameOverOverlay}>
            <span>Game Over! {winner === 'w' ? 'White' : 'Black'} wins!</span>
          </div>
        )}
        <div style={styles.gameArea}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <h2>Stasis Chess</h2>
            <button
              style={{ ...styles.roomButton, backgroundColor: '#dc3545' }}
              onClick={() => {
                setCurrentView('lobby');
                // URL 초기화
                window.history.pushState({}, '', window.location.pathname);
              }}
            >
              로비로 돌아가기
            </button>
          </div>
          <p>Game ID: {gameId}</p>
          <Board pieces={gameState.pieces} onSelect={handleSelect} selectedPiece={selectedPiece} legalMoves={legalMoves} />
          <div style={styles.turnInfo}>
            <h3>Turn: {gameState.turn === 'w' ? 'White' : 'Black'}</h3>
            <button
              onClick={toggleConfirmSelection}
              disabled={!selectedPiece && !confirmedPiece}
            >
              Add stun stack
            </button>
            <button onClick={endTurn}>End Turn</button>
          </div>
        </div>
        <div style={styles.sideBar}>
          <Hand color="w" pieces={gameState.pieces} hands={gameState.hands} onSelect={handleSelectFromHand} selectedPiece={selectedPiece} />
          <Hand color="b" pieces={gameState.pieces} hands={gameState.hands} onSelect={handleSelectFromHand} selectedPiece={selectedPiece} />
          <button onClick={() => setShowLog(prev => !prev)}>
            {showLog ? 'Hide Log' : 'Show Log'}
          </button>
          {showLog && (
            <>
              <div style={styles.log}>
                {log.map((l, i) => (<div key={i}>{l}</div>))}
              </div>
            </>
          )}
        </div>
      </div>
    );
  }
}