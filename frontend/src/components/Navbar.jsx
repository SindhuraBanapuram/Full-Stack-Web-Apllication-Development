import { Link, useLocation } from "react-router-dom";

const Navbar = () => {
  const location = useLocation(); // To highlight active page

  return (
    <nav>
      <Link to="/" className={location.pathname === "/" ? "active" : ""}>Home</Link>
      <Link to="/login" className={location.pathname === "/login" ? "active" : ""}>Login</Link>
      <Link to="/register" className={location.pathname === "/register" ? "active" : ""}>Register</Link>
      <Link to="/wishlist" className={location.pathname === "/wishlist" ? "active" : ""}>Wishlist</Link>
    </nav>
  );
};

export default Navbar;
