import { Link, useLocation } from "react-router-dom";
import styles from "./Navbar.css";

const Navbar = () => {
  const location = useLocation();

  return (
    <nav className={styles.navbar}>
      <Link 
        to="/" 
        className={`${styles.navLink} ${location.pathname === "/" ? styles.active : ""}`}
      >
        Home
      </Link>
      
      <Link 
        to="/wishlist" 
        className={`${styles.navLink} ${location.pathname === "/wishlist" ? styles.active : ""}`}
      >
        Wishlist
      </Link>
      
      <Link 
        to="/notifications" 
        className={`${styles.navLink} ${location.pathname === "/notifications" ? styles.active : ""}`}
      >
        Price Alerts
      </Link>
      
      <Link 
        to="/login" 
        className={`${styles.navLink} ${location.pathname === "/login" ? styles.active : ""}`}
      >
        Logout
      </Link>
    </nav>
  );
};

export default Navbar;