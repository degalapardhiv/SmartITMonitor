import { useNavigate } from "react-router-dom";
import { useAuth } from "../../context/AuthContext";

function LogoutButton() {
  const navigate = useNavigate();
  const { logoutUser } = useAuth();

  function handleLogout() {
    logoutUser();
    navigate("/login");
  }

  return (
    <button
      onClick={handleLogout}
      className="bg-red-600 hover:bg-red-700 text-white px-4 py-2 rounded-lg transition"
    >
      Logout
    </button>
  );
}

export default LogoutButton;
