import axios from "axios";

const API = "/api";


export async function login(username, password){

  const response = await axios.post(
    `${API}/login`,
    new URLSearchParams({
      username,
      password
    }),
    {
      headers:{
        "Content-Type":"application/x-www-form-urlencoded"
      }
    }
  );

  if(response.data.access_token){

    localStorage.setItem(
      "token",
      response.data.access_token
    );

  }

  if(response.data.role){

    localStorage.setItem(
      "role",
      response.data.role
    );

  }

  return response.data;

}


export function getToken(){

  return localStorage.getItem(
    "token"
  );

}


export function getRole(){

  return localStorage.getItem(
    "role"
  );

}


export function logout(){

  localStorage.removeItem(
    "token"
  );

  localStorage.removeItem(
    "role"
  );

}
