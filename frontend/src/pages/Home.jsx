import { useState, useEffect } from "react";
import styles from "./Home.module.css";

const Home = () => {
  const [products, setProducts] = useState([]);

  useEffect(() => {
    fetch("http://localhost:5000/products")
      .then((res) => res.json())
      .then((data) => setProducts(data))
      .catch((error) => console.error("Error fetching products:", error));
  }, []);

  const addToWishlist = (product) => {
    fetch("http://127.0.0.1:5000/wishlist", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        product_id: product.id,
        name: product.name,
        price: product.price,
        image_url: product.image_url,
      }),
    })
      .then((res) => res.json())
      .then((data) => {
        console.log(data);
        alert(data.message);
      })
      .catch((err) => console.error("Error adding to wishlist:", err));
  };

  const openAmazonSearch = () => {
    window.open(
      "https://www.amazon.com/s?k=phones&language=en_US&crid=3A15I2OVN30B3&currency=INR&sprefix=phones%2Caps%2C384&ref=nb_sb_noss_1",
      "_blank"
    );
  };

  return (
    <div className={styles.container}>
      <div className={styles.productsGrid}>
        {products.map((product) => (
          <div key={product.id} className={styles.productCard}>
            <div className={styles.productContent}>
              <img 
                src={product.image_url} 
                alt={product.name} 
                className={styles.productImage} 
              />
              <h3 className={styles.productName}>{product.name}</h3>
              <p className={styles.productPrice}>¥{product.price}</p>
            </div>
            <div className={styles.buttonGroup}>
              <button 
                className={styles.wishlistButton}
                onClick={() => addToWishlist(product)}
              >
                Add to Wishlist
              </button>
              <button 
                className={styles.viewButton}
                onClick={openAmazonSearch}
              >
                View
              </button>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};

export default Home;