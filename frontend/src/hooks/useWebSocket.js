import { useEffect, useState } from "react";

function useWebSocket(){

  const [data,setData] = useState(null);


  useEffect(()=>{

    const protocol =
      window.location.protocol === "https:"
      ? "wss"
      : "ws";


    const socket = new WebSocket(
      `${protocol}://${window.location.host}/ws`
    );


    socket.onmessage = (event)=>{

      try {

        const message = JSON.parse(
          event.data
        );

        setData(message);

      } catch(error) {

        console.log(
          "Invalid websocket data:",
          event.data
        );

      }

    };


    return ()=>socket.close();


  },[]);


  return data;

}

export default useWebSocket;
