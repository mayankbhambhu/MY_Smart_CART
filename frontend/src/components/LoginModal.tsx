import { useState, type FormEvent } from "react";
import { useAuth } from "../context/AuthContext";
import { api, ApiError } from "../lib/api";
import Modal from "./Modal";

export default function LoginModal() {
  const { closeLogin, completeLogin } = useAuth();
  const [step, setStep] = useState<"phone" | "otp">("phone");
  const [phone, setPhone] = useState("");
  const [otp, setOtp] = useState("");
  const [devOtp, setDevOtp] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const sendOtp = async (e?: FormEvent) => {
    e?.preventDefault();
    setBusy(true);
    setError(null);
    try {
      const res = await api.requestOtp(phone);
      setDevOtp(res.dev_otp);
      setOtp("");
      setStep("otp");
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Couldn't send OTP. Is the server running?");
    } finally {
      setBusy(false);
    }
  };

  const verify = async (e: FormEvent) => {
    e.preventDefault();
    setBusy(true);
    setError(null);
    try {
      const res = await api.verifyOtp(phone, otp);
      completeLogin(res.access_token, res.user);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Couldn't verify OTP");
    } finally {
      setBusy(false);
    }
  };

  return (
    <Modal onClose={closeLogin}>
      <div className="login">
        <button className="icon-btn login-close" onClick={closeLogin} aria-label="Close">
          ✕
        </button>
        <div className="brand-badge">
          smart<span>cart</span>
        </div>
        {step === "phone" ? (
          <form onSubmit={sendOtp}>
            <h2>India's last minute app</h2>
            <p className="muted">Log in or sign up</p>
            <label className="phone-input">
              <span>+91</span>
              <input
                autoFocus
                inputMode="numeric"
                maxLength={10}
                placeholder="Enter mobile number"
                value={phone}
                onChange={(e) => setPhone(e.target.value.replace(/\D/g, ""))}
                aria-label="Mobile number"
              />
            </label>
            {error && <p className="error-text">{error}</p>}
            <button className="btn btn-primary btn-block" disabled={phone.length !== 10 || busy}>
              {busy ? "Sending…" : "Continue"}
            </button>
            <p className="muted small">Store staff? Log in with 9999999999 to open the staff dashboard.</p>
          </form>
        ) : (
          <form onSubmit={verify}>
            <h2>OTP verification</h2>
            <p className="muted">
              We've sent a verification code to <strong>+91 {phone}</strong>{" "}
              <button type="button" className="link-btn" onClick={() => setStep("phone")}>
                Change
              </button>
            </p>
            <input
              className="otp-input"
              autoFocus
              inputMode="numeric"
              maxLength={6}
              placeholder="● ● ● ● ● ●"
              value={otp}
              onChange={(e) => setOtp(e.target.value.replace(/\D/g, ""))}
              aria-label="OTP"
            />
            {devOtp && (
              <p className="dev-hint">
                Dev mode OTP: <strong>{devOtp}</strong>{" "}
                <button type="button" className="link-btn" onClick={() => setOtp(devOtp)}>
                  Fill
                </button>
              </p>
            )}
            {error && <p className="error-text">{error}</p>}
            <button className="btn btn-primary btn-block" disabled={otp.length !== 6 || busy}>
              {busy ? "Verifying…" : "Verify & continue"}
            </button>
            <button type="button" className="link-btn" onClick={() => sendOtp()} disabled={busy}>
              Resend code
            </button>
          </form>
        )}
      </div>
    </Modal>
  );
}
