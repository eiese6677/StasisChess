// client/src/App.jsx (간단 예시)
import { useEffect, useState } from "react";
import { io } from "socket.io-client";

const socket = io("http://localhost:5000");

export default function App() {
  const [state, setState] = useState(null);
  const [log, setLog] = useState([]);

  useEffect(() => {
    socket.on("connect", () => {
      console.log("connected", socket.id);
    });
    socket.on("game_state", (g) => {
      setState(g);
    });
    socket.on("move_accepted", (d) => {
      setLog(l => [...l, "move_accepted: " + JSON.stringify(d)]);
    });
    socket.on("move_rejected", (d) => {
      setLog(l => [...l, "move_rejected: " + JSON.stringify(d)]);
    });
    socket.on("drop_rejected", (d) => {
      setLog(l => [...l, "drop_rejected: " + JSON.stringify(d)]);
    });
    // cleanup
    return () => {
      socket.off();
    }
  }, []);

  // 샘플: 가상의 화이트 플레이어가 e2(4,1)에서 e3(4,2)로 이동 요청
  const sampleMove = () => {
    socket.emit("move_request", {
      player_color: "w",
      piece_id: "w_P0",   // 실제로는 UI가 선택한 piece id
      from: [4, 1],
      to: [4, 2]
    });
  };

  // 샘플 drop: 화이트 킹을 (4,0)에 착수
  const sampleDropKing = () => {
    socket.emit("drop_request", {
      player_color: "w",
      piece_id: "w_K0",
      to: [4, 0]
    });
  };

  const endTurn = () => socket.emit("end_turn");

  return (
    <div style={{ padding: 20 }}>
      <h2>StasisChess - Client Sample</h2>
      <button onClick={sampleDropKing}>White drop King (4,0)</button>
      <button onClick={sampleMove}>
        {"Sample Move (w_P0 e2->e3)"}
      </button>

      <button onClick={endTurn}>End Turn</button>

      <h3>Log</h3>
      <div style={{ whiteSpace: 'pre-wrap' }}>
        {log.map((l, i) => (<div key={i}>{l}</div>))}
      </div>

      <h3>Game state (raw)</h3>
      <pre style={{ maxHeight: 300, overflow: 'auto' }}>{JSON.stringify(state, null, 2)}</pre>
    </div>
  );
}
