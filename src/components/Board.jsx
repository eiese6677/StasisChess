// src/components/Board.jsx
import React from 'react';
import Piece from './Piece';

const files = ['a', 'b', 'c', 'd', 'e', 'f', 'g', 'h'];
const ranks = ['1', '2', '3', '4', '5', '6', '7', '8'].reverse();

const style = {
  width: '400px',
  height: '400px',
  display: 'grid',
  gridTemplateColumns: 'repeat(8, 1fr)',
  gridTemplateRows: 'repeat(8, 1fr)',
  border: '2px solid #333'
};

const staticCellStyle = {
  width: '50px',
  height: '50px',
  display: 'flex',
  justifyContent: 'center',
  alignItems: 'center'
};

const Cell = ({ x, y, piece, onSelect, isSelected }) => {
  const isBlack = (x + y) % 2 === 1;
  const cellColor = isBlack ? '#b58863' : '#f0d9b5';
  const cellStyle = {
    ...staticCellStyle,
    backgroundColor: cellColor,
  };

  return (
    <div style={cellStyle} onClick={() => onSelect(x, y, piece)}>
      {piece && <Piece type={piece.type} color={piece.color} stun={piece.stun} moveStack={piece.move_stack} isSelected={isSelected} />}
    </div>
  );
};

export default function Board({ pieces, onSelect, selectedPiece }) {
  const board = Array(8).fill(null).map(() => Array(8).fill(null));
  for (const pieceId in pieces) {
    const piece = pieces[pieceId];
    if (piece.pos) {
      const [x, y] = piece.pos;
      if(x >= 0 && x < 8 && y >= 0 && y < 8) {
        board[y][x] = piece;
      }
    }
  }

  return (
    <div style={style}>
      {ranks.map((rank, y_idx) =>
        files.map((file, x_idx) => {
          // board is indexed by [y][x] but our display iterates y from 7 down to 0
          const y = 7 - y_idx;
          const x = x_idx;
          const pieceOnBoard = board[y][x];
          const isSelected = selectedPiece && pieceOnBoard && selectedPiece.id === pieceOnBoard.id;
          return <Cell key={`${x}-${y}`} x={x} y={y} piece={pieceOnBoard} onSelect={onSelect} isSelected={isSelected} />;
        })
      )}
    </div>
  );
}
