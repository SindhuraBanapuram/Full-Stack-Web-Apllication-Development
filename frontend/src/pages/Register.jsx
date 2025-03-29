import { useState } from "react";
import { useNavigate } from "react-router-dom";
import styles from "./Register.module.css";

const Register = () => {
  const [username, setUsername] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [passwordError, setPasswordError] = useState("");
  const navigate = useNavigate();

  const validatePassword = (password) => {
    const minLength = 8;
    const hasUpperCase = /[A-Z]/.test(password);
    const hasLowerCase = /[a-z]/.test(password);
    const hasNumber = /\d/.test(password);
    const hasSpecialChar = /[!@#$%^&*(),.?":{}|<>]/.test(password);

    if (password.length < minLength) {
      return "Password must be at least 8 characters long";
    }
    if (!hasUpperCase) {
      return "Password must contain at least one uppercase letter";
    }
    if (!hasLowerCase) {
      return "Password must contain at least one lowercase letter";
    }
    if (!hasNumber) {
      return "Password must contain at least one number";
    }
    if (!hasSpecialChar) {
      return "Password must contain at least one special character";
    }
    return "";
  };

  const handlePasswordChange = (e) => {
    const newPassword = e.target.value;
    setPassword(newPassword);
    setPasswordError(validatePassword(newPassword));
  };

  const handleRegister = async (e) => {
    e.preventDefault();
    const error = validatePassword(password);
    if (error) {
      setPasswordError(error);
      return;
    }

    const response = await fetch("http://localhost:5000/register", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ username, email, password })
    });
    const data = await response.json();
    if (response.ok) {
      alert("Registration successful");
    } else {
      alert(data.error || "Registration failed");
    }
  };

  return (
    <div className={styles.container}>
      <h2 className={styles.title}>Register</h2>
      <form className={styles.form} onSubmit={handleRegister}>
        <input className={styles.input} type="text" placeholder="Username" value={username} onChange={(e) => setUsername(e.target.value)} required />
        <input className={styles.input} type="email" placeholder="Email" value={email} onChange={(e) => setEmail(e.target.value)} required />
        <div className={styles.passwordContainer}>
          <input 
            className={`${styles.input} ${passwordError && styles.inputError}`}
            type="password" 
            placeholder="Password" 
            value={password} 
            onChange={handlePasswordChange} 
            required 
          />
          {password && (
            <div className={styles.passwordStrength}>
              <div className={`
                ${styles.strengthBar} 
                ${password.length >= 8 ? styles.valid : ''}
              `}></div>
              <div className={`
                ${styles.strengthBar} 
                ${/[A-Z]/.test(password) ? styles.valid : ''}
              `}></div>
              <div className={`
                ${styles.strengthBar} 
                ${/[a-z]/.test(password) ? styles.valid : ''}
              `}></div>
              <div className={`
                ${styles.strengthBar} 
                ${/\d/.test(password) ? styles.valid : ''}
              `}></div>
              <div className={`
                ${styles.strengthBar} 
                ${/[!@#$%^&*(),.?":{}|<>]/.test(password) ? styles.valid : ''}
              `}></div>
            </div>
          )}
          {passwordError && <div className={styles.errorMessage}>{passwordError}</div>}
        </div>
        <button 
          className={styles.button} 
          type="submit"
          disabled={!!passwordError}
        >
          Register
        </button>
        <div className={styles.loginPrompt}>
          Already have an account? <span className={styles.loginLink} onClick={() => navigate("/login")}>Login</span>
        </div>
      </form>
    </div>
  );
};

export default Register;