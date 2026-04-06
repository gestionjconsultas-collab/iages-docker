// frontend/src/socket.js
import { io } from 'socket.io-client';
import { BACKEND_URL } from './utils/urls';

const socket = io(BACKEND_URL, {
    withCredentials: true,
    autoConnect: true,
    transports: ['websocket', 'polling']
});

export default socket;