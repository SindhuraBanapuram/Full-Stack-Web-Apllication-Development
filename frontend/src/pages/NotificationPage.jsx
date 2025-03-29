import { useState, useEffect } from 'react';
import styles from './Notification.module.css';
import { useNavigate } from 'react-router-dom';

const NotificationPage = () => {
  const [notifications, setNotifications] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const navigate = useNavigate();

  useEffect(() => {
    const fetchNotifications = async () => {
      try {
        const response = await fetch('http://localhost:5000/notifications');
        if (!response.ok) {
          throw new Error('Failed to fetch notifications');
        }
        const data = await response.json();
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
              onClick={() => navigate(`/product/${notification.productId}`)}
            >
              <img 
                src={notification.imageUrl} 
                alt={notification.productName}
                className={styles.productImage}
                onError={(e) => e.target.src = '/placeholder-product.png'}
              />
              <div className={styles.notificationContent}>
                <h3>{notification.productName}</h3>
                <p className={styles.priceComparison}>
                  <span className={styles.oldPrice}>¥{notification.oldPrice}</span>
                  <span> → </span>
                  <span className={styles.newPrice}>¥{notification.newPrice}</span>
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