import { useEffect, useRef, useState } from "react";


const START_BACKOFF_MS = 1000;

const MAX_BACKOFF_MS = 30000;


let socket = null;

let reconnectTimer = null;

let reconnectAttempt = 0;

let subscriberCount = 0;

let disconnectTimer = null;

let currentStatus = "idle";


const subscribers = new Set();

const statusListeners = new Set();


export function getWsUrl() {

  const protocol =
    window.location.protocol === "https:"
    ? "wss"
    : "ws";

  return `${protocol}://${window.location.host}/ws`;

}


function setStatus(status) {

  currentStatus = status;

  statusListeners.forEach(cb => {

    try {
      cb(status);
    }
    catch (err) {
      console.error(err);
    }

  });

}


function clearTimers() {

  if (reconnectTimer) {

    clearTimeout(reconnectTimer);

    reconnectTimer = null;

  }

  if (disconnectTimer) {

    clearTimeout(disconnectTimer);

    disconnectTimer = null;

  }

}


function scheduleReconnect() {

  clearTimers();

  if (subscriberCount <= 0) return;

  const base = Math.min(
    START_BACKOFF_MS * Math.pow(2, reconnectAttempt),
    MAX_BACKOFF_MS
  );

  const jitter = Math.random() * base * 0.3;

  const delay = base + jitter;

  reconnectAttempt += 1;

  reconnectTimer = setTimeout(connect, delay);

}


function connect() {

  if (socket) return;

  setStatus("connecting");

  socket = new WebSocket(getWsUrl());

  socket.onopen = () => {

    reconnectAttempt = 0;

    setStatus("open");

  };

  socket.onmessage = (event) => {

    let message;

    try {

      message = JSON.parse(event.data);

    }
    catch {

      console.log(
        "Invalid websocket data:",
        event.data
      );

      return;

    }

    if (!message || message.type === "ping") return;

    subscribers.forEach(ref => {

      try {
        ref.current(message);
      }
      catch (err) {
        console.error(err);
      }

    });

  };

  socket.onerror = () => {

    setStatus("error");

    if (socket) {

      socket.close();

    }

  };

  socket.onclose = () => {

    socket = null;

    setStatus("disconnected");

    scheduleReconnect();

  };

}


function disconnect() {

  clearTimers();

  if (socket) {

    socket.onopen = null;

    socket.onmessage = null;

    socket.onerror = null;

    socket.onclose = null;

    socket.close();

    socket = null;

  }

  reconnectAttempt = 0;

  setStatus("idle");

}


function maybeDisconnect() {

  if (subscriberCount > 0) return;

  clearTimeout(disconnectTimer);

  disconnectTimer = setTimeout(() => {

    if (subscriberCount > 0) return;

    disconnect();

  }, 500);

}


export function getSocketStatus() {

  return currentStatus;

}


export function useSocketStatus() {

  const [status, setStatusState] = useState(getSocketStatus());

  useEffect(() => {

    const update = (next) => setStatusState(next);

    statusListeners.add(update);

    update(getSocketStatus());

    return () => statusListeners.delete(update);

  }, []);

  return status;

}


function useWebSocket(callback) {

  const callbackRef = useRef(callback);


  useEffect(() => {

    callbackRef.current = callback;

  });


  useEffect(() => {

    subscriberCount += 1;

    connect();

    subscribers.add(callbackRef);

    return () => {

      subscriberCount = Math.max(0, subscriberCount - 1);

      subscribers.delete(callbackRef);

      maybeDisconnect();

    };

  }, []);

}


export default useWebSocket;
