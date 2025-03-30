import { useState } from "react";
import { useNavigate } from "react-router-dom";
import styles from "./Register.module.css";

const Register = () => {
  const [username, setUsername] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [passwordStrength, setPasswordStrength] = useState("");
  const [passwordFocused, setPasswordFocused] = useState(false);
  const navigate = useNavigate();

  const checkPasswordStrength = (password) => {
    const hasUpperCase = /[A-Z]/.test(password);
    const hasLowerCase = /[a-z]/.test(password);
    const hasNumber = /\d/.test(password);
    const hasSpecialChar = /[!@#$%^&*(),.?":{}|<>]/.test(password);
    const isLongEnough = password.length >= 8;

    if (!isLongEnough || !hasUpperCase || !hasLowerCase || !hasNumber || !hasSpecialChar) {
      return "Weak 🔴";
    }
    return "Strong 🟢";
  };

  const handlePasswordChange = (e) => {
    const newPassword = e.target.value;
    setPassword(newPassword);
    setPasswordStrength(checkPasswordStrength(newPassword));
  };

  const handleRegister = async (e) => {
    e.preventDefault();
    if (passwordStrength === "Weak 🔴") {
      alert("Please choose a stronger password.");
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
      navigate("/");
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
            className={styles.input}
            type="password" 
            placeholder="Password" 
            value={password} 
            onChange={handlePasswordChange} 
            onFocus={() => setPasswordFocused(true)}
            required 
          />
          {passwordFocused && !password && (
            <div className={styles.passwordCriteria}>
              <p>Password must contain:</p>
              <ul>
                <li>✅ At least 8 characters</li>
                <li>✅ Uppercase (A-Z) & Lowercase (a-z)</li>
                <li>✅ At least 1 number (0-9)</li>
                <li>✅ At least 1 special character (!@#$%^&*)</li>
              </ul>
            </div>
          )}
          {password && <p className={styles.passwordStrength}>{passwordStrength}</p>}
        </div>

        <button className={styles.button} type="submit">Register</button>
        <div className={styles.loginPrompt}>
          Already have an account? <span className={styles.loginLink} onClick={() => navigate("/")}>Login</span>
        </div>
      </form>
    </div>
  );
};

export default Register;
