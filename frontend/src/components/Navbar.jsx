import { Link, useLocation } from "react-router-dom";
import { FaHeart, FaBell, FaHome, FaSignOutAlt } from "react-icons/fa"; // Import icons
import styles from "./Navbar.css";

const Navbar = () => {
  const location = useLocation();

  return (
    <nav className={styles.navbar}>
      <Link 
        to="/home" 
        className={`${styles.navLink} ${location.pathname === "/home" ? styles.active : ""}`}
      >
        <FaHome className={styles.icon} /> Home
      </Link>
      
      <Link 
        to="/wishlist" 
        className={`${styles.navLink} ${location.pathname === "/wishlist" ? styles.active : ""}`}
      >
        <FaHeart className={styles.icon} /> Wishlist
      </Link>
      
      <Link 
        to="/notifications" 
        className={`${styles.navLink} ${location.pathname === "/notifications" ? styles.active : ""}`}
      >
        <FaBell className={styles.icon} /> Notifications
      </Link>
      
      <Link 
        to="/" 
        className={`${styles.navLink} ${location.pathname === "/" ? styles.active : ""}`}
        onClick={() => window.location.href = "/"}
      >
        <FaSignOutAlt className={styles.icon} /> Logout
      </Link>
    </nav>
  );
};

export default Navbar;
