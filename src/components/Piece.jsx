import React from 'react';

const pieceUnicode = {
  w: { king: '♔', queen: '♕', rook: '♖', bishop: '♗', knight: '♘', pawn: '♙' },
  b: { king: '♚', queen: '♛', rook: '♜', bishop: '♝', knight: '♞', pawn: '♟︎' }
};

const pieceStyle = (isStunned, isSelected) => ({
  position: 'relative',
  fontSize: '36px',
  cursor: 'pointer',
  textAlign: 'center',
  width: '50px',
  height: '50px',
  display: 'flex',
  alignItems: 'center',
  justifyContent: 'center',
  opacity: isStunned ? 0.5 : 1,
  textShadow: isStunned ? '0 0 5px red' : 'none',
  userSelect: 'none', // Prevent text selection and potential dragging
  border: isSelected ? '2px solid blue' : 'none', // Add border for selected piece
  boxSizing: 'border-box' // Ensure border doesn't expand the element
});

const stackStyle = {
  position: 'absolute',
  bottom: 0,
  left: 0,
  right: 0,
  fontSize: '10px',
  fontWeight: 'bold',
  color: 'black',
  textShadow: '0px 0px 3px white, 0px 0px 3px white, 0px 0px 3px white',
  lineHeight: '1',
};

export default function Piece({ type, color, stun, moveStack, onSelect, isSelected }) {
  const isStunned = stun > 0;
  return (
    <div style={pieceStyle(isStunned, isSelected)} onClick={onSelect} draggable="false">
      {pieceUnicode[color][type]}
      {(stun > 0 || moveStack > 0) && (
        <div style={stackStyle}>
          {`S:${stun}`}
          {moveStack > 0 ? ` M:${moveStack}` : ''}
        </div>
      )}
    </div>
  );
}