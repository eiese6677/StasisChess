// src/components/Hand.jsx
import React from 'react';
import Piece from './Piece';

const handStyle = {
    display: 'flex',
    flexWrap: 'wrap',
    minHeight: '50px',
    width: '400px',
    backgroundColor: '#eee',
    padding: '5px',
    marginTop: '10px'
};

const pieceWrapperStyle = {
    margin: '2px',
    border: '1px solid #ccc',
    borderRadius: '4px'
}

export default function Hand({ color, pieces, hands, onSelect, selectedPiece }) {
    const handPieces = hands[color] || [];

    return (
        <div>
            <h4>{color === 'w' ? 'White' : 'Black'}'s Hand</h4>
            <div style={handStyle}>
                {handPieces.map((pid, index) => {
                    const piece = pieces[pid];
                    if (!piece) return null;
                    const isSelected = selectedPiece && selectedPiece.id === pid;
                    return (
                        <div key={`${pid}-${index}`} onClick={() => onSelect(piece)} style={{...pieceWrapperStyle, backgroundColor: isSelected ? 'yellow' : 'transparent'}}>
                           <Piece type={piece.type} color={piece.color} stun={piece.stun} moveStack={piece.move_stack} isSelected={isSelected} />
                        </div>
                    )
                })}
            </div>
        </div>
    );
}
