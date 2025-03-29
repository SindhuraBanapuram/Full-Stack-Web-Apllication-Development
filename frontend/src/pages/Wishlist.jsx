import { useState, useEffect } from "react";
import axios from "axios";

const Wishlist = () => {
  const [wishlist, setWishlist] = useState([]);

  useEffect(() => {
    axios.get("http://localhost:5000/wishlist")
      .then((res) => setWishlist(res.data))
      .catch((error) => console.error("Error fetching wishlist:", error));
  }, []);

  return (
    <div className="p-4">
      <h2 className="text-2xl font-bold mb-4">Your Wishlist</h2>
      <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-4">
        {wishlist.map((product) => (
          <div key={product.id} className="border p-4 rounded-lg shadow-md">
            <img src={product.image_url} alt={product.name} className="w-full h-40 object-cover" />
            <h3 className="text-lg font-bold mt-2">{product.name}</h3>
            <p className="text-green-600 font-semibold">${product.price}</p>
          </div>
        ))}
      </div>
    </div>
  );
};

export default Wishlist;
