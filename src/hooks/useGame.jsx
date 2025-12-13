// src/hooks/useGame.jsx
import { useState, useEffect } from 'react';
import { io } from 'socket.io-client';

const socket = io("http://127.0.0.1:5000");

export const useGame = () => {
  const [gameState, setGameState] = useState(null);
  const [log, setLog] = useState([]);
  const [selectedPiece, setSelectedPiece] = useState(null);
  const [gameId, setGameId] = useState(null);
  const [gameOver, setGameOver] = useState(false);
  const [winner, setWinner] = useState(null);

  useEffect(() => {
    socket.on("connected", (data) => {
        console.log("connected", data.sid);
        setGameId(data.game_id);
    });

    socket.on("game_state", (g) => setGameState(g));
    socket.on("move_accepted", (d) => {
      setLog(l => [`Move accepted: ${JSON.stringify(d)}`, ...l]);
      setSelectedPiece(null);
    });
    socket.on("move_rejected", (d) => setLog(l => [`Move rejected: ${d.reason}`, ...l]));
    socket.on("drop_accepted", (d) => {
      setLog(l => [`Drop accepted: ${JSON.stringify(d)}`, ...l]);
      setSelectedPiece(null);
    });
    socket.on("drop_rejected", (d) => setLog(l => [`Drop rejected: ${d.reason}`, ...l]));
    socket.on("turn_ended", (d) => setLog(l => [`New turn: ${d.turn}'s move`, ...l]));
    socket.on("game_end", (data) => {
        setLog(l => [`Game Over: ${data.winner} wins!`, ...l]);
        setGameOver(true);
        setWinner(data.winner);
        setSelectedPiece(null);
    });

    return () => {
        socket.off("connected");
        socket.off("game_state");
        socket.off("move_accepted");
        socket.off("move_rejected");
        socket.off("drop_accepted");
        socket.off("drop_rejected");
        socket.off("turn_ended");
        socket.off("game_end");
    };
  }, []);

  const handleSelect = (x, y, piece) => {
    if (!gameState || gameOver) return;
    // If a piece is already selected
    if (selectedPiece) {
      // If the selected piece is from hand (a drop)
      if (selectedPiece.captured) {
        if (piece === null) { // Can only drop on empty squares
          console.log(`Requesting drop of ${selectedPiece.id} at (${x}, ${y})`);
          socket.emit("drop_request", {
            player_color: selectedPiece.color,
            piece_id: selectedPiece.id,
            to: [x, y]
          });
        } else {
          console.log("Cannot drop on an occupied square.");
          setSelectedPiece(null); // Deselect on invalid drop
        }
      }
      // If the selected piece is from the board (a move)
      else {
        if (piece && piece.id === selectedPiece.id) {
          setSelectedPiece(null);
          return;
        }
        console.log(`Requesting move of ${selectedPiece.id} from ${selectedPiece.pos} to (${x}, ${y})`);
        socket.emit("move_request", {
          player_color: selectedPiece.color,
          piece_id: selectedPiece.id,
          from: selectedPiece.pos,
          to: [x, y]
        });
      }
    }
    // If no piece is selected yet
    else {
      if (piece && piece.color === gameState.turn) {
        console.log("Selected piece on board:", piece);
        setSelectedPiece(piece);
      }
    }
  };

  const handleSelectFromHand = (piece) => {
    if (!gameState || gameOver) return;
    if (piece.color !== gameState.turn) {
      console.log("Cannot select opponent's piece from hand.");
      return;
    }
    if (selectedPiece && selectedPiece.id === piece.id) {
      setSelectedPiece(null); // Deselect if clicking the same hand piece
    } else {
      console.log("Selected piece from hand:", piece);
      setSelectedPiece(piece);
    }
  };

  const endTurn = () => {
    if (gameOver) return;
    socket.emit("end_turn");
    setSelectedPiece(null);
  };

  return { gameState, log, selectedPiece, gameId, gameOver, winner, handleSelect, handleSelectFromHand, endTurn };
};
