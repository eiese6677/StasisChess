import { useState, useEffect } from 'react';

const styles = {
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

export default function Lobby({ playerSid, socket, onGameReady }) {
    const [rooms, setRooms] = useState([]);

    // 방 목록 가져오기
    const fetchRooms = async () => {
        try {
            const response = await fetch('/api/rooms');
            const data = await response.json();
            setRooms(data.rooms);
        } catch (error) {
            console.error('방 목록 가져오기 실패:', error);
        }
    };

    // 방 생성
    const createRoom = async (roomName) => {
        try {
            const response = await fetch('/api/rooms', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ name: roomName, sid: playerSid })
            });
            const data = await response.json();
            if (data.room) {
                fetchRooms(); // 목록 새로고침
            }
        } catch (error) {
            console.error('방 생성 실패:', error);
        }
    };

    // 방 참가
    const joinRoom = async (roomId) => {
        try {
            const response = await fetch(`/api/rooms/${roomId}/join`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ sid: playerSid })
            });
            const data = await response.json();
            if (data.error) {
                alert(data.error);
            }
        } catch (error) {
            console.error('방 참가 실패:', error);
        }
    };

    useEffect(() => {
        // Socket.IO 이벤트
        socket.on('game_ready', (data) => {
            console.log('Lobby에서 게임 준비됨:', data);
            if (onGameReady) onGameReady(data);
        });

        fetchRooms();

        return () => {
            socket.off('game_ready');
        };
    }, [socket, onGameReady]);

    return (
        <div style={styles.lobby}>
            <h1>Stasis Chess - 방 선택</h1>

            <div style={styles.createRoom}>
                <h3>새로운 방 만들기</h3>
                <input
                    type="text"
                    placeholder="방 이름"
                    id="roomNameInput"
                    style={styles.input}
                />
                <button
                    style={styles.roomButton}
                    onClick={() => {
                        const input = document.getElementById('roomNameInput');
                        const roomName = input.value.trim() || '새로운 게임';
                        createRoom(roomName);
                        input.value = '';
                    }}
                >
                    방 만들기
                </button>
            </div>

            <div>
                <h3>참가 가능한 방</h3>
                <button style={styles.roomButton} onClick={fetchRooms}>
                    새로고침
                </button>

                <div style={styles.roomList}>
                    {rooms.length === 0 ? (
                        <p>참가 가능한 방이 없습니다.</p>
                    ) : (
                        rooms.map(room => (
                            <div key={room.id} style={styles.roomItem}>
                                <div>
                                    <strong>{room.name}</strong>
                                    <br />
                                    <small>상태: {room.status} | 플레이어: {room.player_count}/2</small>
                                </div>
                                <button
                                    style={styles.roomButton}
                                    onClick={() => joinRoom(room.id)}
                                    disabled={room.status !== 'waiting' || room.player_count >= 2}
                                >
                                    참가하기
                                </button>
                            </div>
                        ))
                    )}
                </div>
            </div>
        </div>
    );
}
