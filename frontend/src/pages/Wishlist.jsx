import { useState, useEffect } from "react";
import axios from "axios";
import styles from "./Wishlist.module.css";

const Wishlist = () => {
  const [wishlist, setWishlist] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    const fetchWishlist = async () => {
      try {
        const response = await axios.get("http://localhost:5000/wishlist");
        const validatedWishlist = response.data.map(item => ({
          ...item,
          id: item.product_id || item._id || Math.random().toString(36).substr(2, 9) 
        }));
        setWishlist(validatedWishlist);
      } catch (err) {
        console.error("Error fetching wishlist:", err);
        setError("Failed to load wishlist. Please try again later.");
      } finally {
        setLoading(false);
      }
    };

    fetchWishlist();
  }, []);

  const removeFromWishlist = async (productId) => {
    if (!productId) {
      console.error("Invalid product ID:", productId);
      alert("Error: Invalid product ID");
      return;
    }

    try {
      console.log("Deleting product with ID:", productId); 
      await axios.delete(`http://localhost:5000/wishlist/${productId}`);
      setWishlist(prev => prev.filter(item => item.id !== productId));
    } catch (err) {
      console.error("Error removing from wishlist:", err);
      alert(`Failed to remove item: ${err.response?.data?.message || err.message}`);
    }
  };

  if (loading) {
    return (
      <div className={styles.container}>
        <h2 className={styles.title}>Your Wishlist</h2>
        <div className={styles.loadingSpinner}></div>
        <p className={styles.loadingMessage}>Loading your wishlist...</p>
      </div>
    );
  }

  if (error) {
    return (
      <div className={styles.container}>
        <h2 className={styles.title}>Your Wishlist</h2>
        <p className={styles.errorMessage}>{error}</p>
        <button 
          className={styles.retryButton}
          onClick={() => window.location.reload()}
        >
          Retry
        </button>
      </div>
    );
  }

  return (
    <div className={styles.container}>
      <h2 className={styles.title}>Your Wishlist</h2>
      
      {wishlist.length === 0 ? (
        <div className={styles.emptyState}>
          <p className={styles.emptyMessage}>Your wishlist is empty</p>
          <button 
            className={styles.browseButton}
            onClick={() => window.location.href = "/Home"}
          >
            Browse Products
          </button>
        </div>
      ) : (
        <div className={styles.productsGrid}>
          {wishlist.map((product) => {
            console.log("Rendering product:", product);
            return (
              <div key={product.id} className={styles.productCard}>
                <img 
                  src={product.image_url || '/placeholder-product.jpg'} 
                  alt={product.name} 
                  className={styles.productImage}
                  onError={(e) => {
                    e.target.src = '/placeholder-product.jpg';
                  }}
                />
                <div className={styles.productDetails}>
                  <h3 className={styles.productName}>{product.name}</h3>
                  <p className={styles.productPrice}>¥{product.price}</p>
                </div>
                <button
                  className={styles.removeButton}
                  onClick={() => removeFromWishlist(product.id)}
                  aria-label={`Remove ${product.name} from wishlist`}
                >
                  Remove
                </button>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
};

export default Wishlist;
