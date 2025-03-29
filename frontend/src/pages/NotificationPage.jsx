import { useState, useEffect } from 'react';
import styles from './Notification.module.css';
import { useNavigate } from 'react-router-dom';

const NotificationPage = () => {
  const [notifications, setNotifications] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const navigate = useNavigate();

  // Fetch notifications from the backend
  useEffect(() => {
    const fetchNotifications = async () => {
      try {
        const response = await fetch('http://localhost:5000/notifications');
        if (!response.ok) {
          throw new Error('Failed to fetch notifications');
        }
        const data = await response.json();
        console.log('Fetched notifications:', data);
        setNotifications(data);
      } catch (error) {
        console.error('Error fetching notifications:', error);
        setError(error.message);
      } finally {
        setLoading(false);
      }
    };

    fetchNotifications();
  }, []);

  // Function to add a new notification
  const addNotification = async (notificationData) => {
    try {
      const response = await fetch('http://localhost:5000/notifications', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(notificationData),
      });

      if (!response.ok) {
        throw new Error('Failed to add notification');
      }

      const result = await response.json();
      console.log('Notification added:', result);

      setNotifications((prev) => [...prev, result]); // Update UI with new notification
    } catch (error) {
      console.error('Error adding notification:', error);
    }
  };

  if (loading) {
    return (
      <div className={styles.container}>
        <h1>Your Price Alerts</h1>
        <p>Loading notifications...</p>
      </div>
    );
  }

  if (error) {
    return (
      <div className={styles.container}>
        <h1>Your Price Alerts</h1>
        <p className={styles.error}>{error}</p>
        <button onClick={() => window.location.reload()}>Retry</button>
      </div>
    );
  }

  return (
    <div className={styles.container}>
      <h1>Your Price Alerts</h1>
      <div className={styles.notificationList}>
        {notifications.length > 0 ? (
          notifications.map((notification) => (
            <div 
              key={notification.id} 
              className={styles.notificationCard}
              onClick={() => navigate(`/product/${notification.product_id}`)}
            >
              <img 
                src={notification.image_url} 
                alt={notification.product_name}
                className={styles.productImage}
                onError={(e) => e.target.src = '/placeholder-product.png'}
              />
              <div className={styles.notificationContent}>
                <h3>{notification.product_name}</h3>
                <p className={styles.priceComparison}>
                  <span className={styles.oldPrice}>${notification.old_price}</span>
                  <span> → </span>
                  <span className={styles.newPrice}>${notification.new_price}</span>
                </p>
                <p className={styles.timestamp}>
                  {new Date(notification.timestamp).toLocaleString()}
                </p>
              </div>
            </div>
          ))
        ) : (
          <p className={styles.emptyMessage}>No price drop alerts yet</p>
        )}
      </div>
    </div>
  );
};

export default NotificationPage;
