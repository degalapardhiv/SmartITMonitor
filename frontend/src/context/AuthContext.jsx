import { createContext, useContext, useState, useEffect } from "react";
import { getToken, getRole, logout } from "../services/auth";

const AuthContext = createContext();

export function AuthProvider({ children }) {
  const [token, setToken] = useState(getToken());
  const [role, setRole] = useState(getRole());
  const [username, setUsername] = useState(localStorage.getItem("username"));

  useEffect(() => {
    setToken(getToken());
    setRole(getRole());
  }, []);

  const loginUser = (token, role, username) => {
    localStorage.setItem("token", token);
    localStorage.setItem("role", role);
    localStorage.setItem("username", username);

    setToken(token);
    setRole(role);
    setUsername(username);
  };

  const logoutUser = () => {
    logout();
    localStorage.removeItem("username");
    setToken(null);
    setRole(null);
    setUsername(null);
  };

  return (
    <AuthContext.Provider
      value={{
        token,
        role,
        username,
        loginUser,
        logoutUser,
        isAuthenticated: !!token,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  return useContext(AuthContext);
}
