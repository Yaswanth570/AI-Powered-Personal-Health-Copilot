import {
  AlertCircle,
  ArrowRight,
  Check,
  Eye,
  EyeOff,
  HeartPulse,
  Lock,
  Mail,
  ShieldCheck,
  Sparkles,
  User,
} from "lucide-react";
import React, { useId, useMemo, useState } from "react";
import { useAuth } from "../../context/AuthContext";
import { Button } from "../ui/button";
import { Input } from "../ui/input";

interface RegisterPageProps {
  onSwitchToLogin: () => void;
}

interface PasswordCriteria {
  label: string;
  met: boolean;
}

export const RegisterPage: React.FC<RegisterPageProps> = ({ onSwitchToLogin }) => {
  const { register } = useAuth();
  const [fullName, setFullName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [showConfirmPassword, setShowConfirmPassword] = useState(false);
  const [hasAgreedToPrivacy, setHasAgreedToPrivacy] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  const fullNameId = useId();
  const emailId = useId();
  const passwordId = useId();
  const confirmPasswordId = useId();
  const privacyId = useId();
  const errorId = useId();

  // Password strength evaluation
  const criteria: PasswordCriteria[] = useMemo(() => {
    return [
      { label: "At least 8 characters", met: password.length >= 8 },
      { label: "Includes uppercase & lowercase letters", met: /[a-z]/.test(password) && /[A-Z]/.test(password) },
      { label: "Includes at least one number (0-9)", met: /\d/.test(password) },
      { label: "Includes a special character (@, $, !, %, etc.)", met: /[^A-Za-z0-9]/.test(password) },
    ];
  }, [password]);

  const strengthScore = useMemo(() => {
    return criteria.filter((c) => c.met).length;
  }, [criteria]);

  const strengthMeta = useMemo(() => {
    if (strengthScore <= 1) return { label: "Weak", color: "bg-red-500", text: "text-red-700" };
    if (strengthScore === 2) return { label: "Fair", color: "bg-amber-500", text: "text-amber-700" };
    if (strengthScore === 3) return { label: "Good", color: "bg-teal-600", text: "text-teal-700" };
    return { label: "Strong", color: "bg-emerald-600", text: "text-emerald-700" };
  }, [strengthScore]);

  async function handleRegister(e: React.FormEvent) {
    e.preventDefault();
    setErrorMessage(null);

    const cleanName = fullName.trim();
    const cleanEmail = email.trim();

    if (!cleanName || cleanName.length < 2) {
      setErrorMessage("Please enter your full legal name or clinical identifier (min 2 characters).");
      return;
    }
    if (!cleanEmail || !cleanEmail.includes("@")) {
      setErrorMessage("Please provide a valid email address.");
      return;
    }
    if (password.length < 8) {
      setErrorMessage("Password must be at least 8 characters in length.");
      return;
    }
    if (password !== confirmPassword) {
      setErrorMessage("Password and confirmation password do not match.");
      return;
    }
    if (!hasAgreedToPrivacy) {
      setErrorMessage("Please acknowledge the patient data isolation and clinical privacy notice.");
      return;
    }

    setIsLoading(true);
    try {
      await register({
        full_name: cleanName,
        email: cleanEmail,
        password,
      });
    } catch (err: unknown) {
      const msg =
        err instanceof Error
          ? err.message
          : "Registration failed. Please verify your details.";
      setErrorMessage(msg);
    } finally {
      setIsLoading(false);
    }
  }

  return (
    <main className="flex min-h-screen items-center justify-center bg-background px-4 py-8 sm:px-6 lg:px-8">
      <div className="w-full max-w-5xl overflow-hidden rounded-2xl border border-border bg-card shadow-xl lg:grid lg:grid-cols-12">
        {/* Left Clinical Brand Showcase */}
        <section
          aria-label="Clinical Tenancy and Privacy"
          className="relative flex flex-col justify-between bg-primary p-8 text-primary-foreground sm:p-12 lg:col-span-5"
        >
          <div className="space-y-6">
            <div className="flex items-center gap-2.5">
              <div className="flex h-11 w-11 items-center justify-center rounded-xl bg-primary-foreground/10 ring-1 ring-primary-foreground/20 backdrop-blur-sm">
                <HeartPulse className="h-6 w-6 text-primary-foreground" />
              </div>
              <div>
                <span className="font-display text-lg font-semibold tracking-tight">
                  Personal Health Copilot
                </span>
                <span className="block text-xs text-primary-foreground/70">
                  AI-Powered Medical Memory
                </span>
              </div>
            </div>

            <div className="space-y-3 pt-4">
              <span className="inline-flex items-center gap-1.5 rounded-full bg-primary-foreground/15 px-3 py-1 text-xs font-medium text-primary-foreground ring-1 ring-primary-foreground/20">
                <Sparkles className="h-3.5 w-3.5" />
                Automatic Tenancy Provisioning
              </span>
              <h2 className="font-display text-2xl font-medium leading-snug sm:text-3xl">
                Create your private, HIPAA-grade clinical account.
              </h2>
              <p className="text-sm leading-relaxed text-primary-foreground/80">
                Registering creates a dedicated medical memory workspace. Your primary patient profile
                is automatically configured, and all uploaded medical records and chat consultations
                remain cryptographically isolated to your account.
              </p>
            </div>

            <ul className="space-y-3 pt-2 text-xs sm:text-sm text-primary-foreground/90">
              <li className="flex items-center gap-2.5">
                <ShieldCheck className="h-4 w-4 shrink-0 text-emerald-300" />
                <span>Zero model training on your private medical history</span>
              </li>
              <li className="flex items-center gap-2.5">
                <ShieldCheck className="h-4 w-4 shrink-0 text-emerald-300" />
                <span>Dedicated PostgreSQL patient isolation schema</span>
              </li>
              <li className="flex items-center gap-2.5">
                <ShieldCheck className="h-4 w-4 shrink-0 text-emerald-300" />
                <span>Bcrypt password hashing & stateless JWT authorization</span>
              </li>
            </ul>
          </div>

          <div className="mt-8 border-t border-primary-foreground/15 pt-6 text-xs text-primary-foreground/75">
            <p>Ready to deploy across hospital clinics or personal care workflows.</p>
          </div>
        </section>

        {/* Right Registration Form */}
        <section
          aria-label="Registration Form"
          className="flex flex-col justify-center p-6 sm:p-10 lg:col-span-7"
        >
          <div className="mx-auto w-full max-w-md space-y-6">
            <header className="space-y-1.5">
              <h1 className="font-display text-2xl font-semibold tracking-tight text-foreground sm:text-3xl">
                Create your account
              </h1>
              <p className="text-sm text-muted-foreground">
                Set up your credentials to provision your clinical workspace.
              </p>
            </header>

            {/* Error Banner */}
            {errorMessage ? (
              <div
                id={errorId}
                role="alert"
                aria-live="polite"
                className="flex items-start gap-3 rounded-lg border border-red-200 bg-red-50 p-3.5 text-sm text-red-900"
              >
                <AlertCircle className="mt-0.5 h-4 w-4 shrink-0 text-red-600" />
                <div className="flex-1">
                  <p className="font-medium">Registration Issue</p>
                  <p className="mt-0.5 text-xs leading-relaxed text-red-700">{errorMessage}</p>
                </div>
              </div>
            ) : null}

            <form onSubmit={handleRegister} className="space-y-4" noValidate>
              <div className="space-y-1.5">
                <label
                  htmlFor={fullNameId}
                  className="block text-xs font-medium uppercase tracking-wide text-foreground"
                >
                  Full Name / Patient Name
                </label>
                <div className="relative">
                  <User
                    className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground"
                    aria-hidden="true"
                  />
                  <Input
                    id={fullNameId}
                    type="text"
                    name="fullName"
                    value={fullName}
                    onChange={(e) => setFullName(e.target.value)}
                    placeholder="e.g. Dr. Ramesh Kumar or Smt. Priya Sharma"
                    autoComplete="name"
                    required
                    disabled={isLoading}
                    aria-invalid={Boolean(errorMessage)}
                    aria-describedby={errorMessage ? errorId : undefined}
                    className="pl-9 text-sm"
                  />
                </div>
              </div>

              <div className="space-y-1.5">
                <label
                  htmlFor={emailId}
                  className="block text-xs font-medium uppercase tracking-wide text-foreground"
                >
                  Email Address
                </label>
                <div className="relative">
                  <Mail
                    className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground"
                    aria-hidden="true"
                  />
                  <Input
                    id={emailId}
                    type="email"
                    name="email"
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    placeholder="user@healthcopilot.local or doctor@domain.com"
                    autoComplete="email"
                    required
                    disabled={isLoading}
                    aria-invalid={Boolean(errorMessage)}
                    aria-describedby={errorMessage ? errorId : undefined}
                    className="pl-9 text-sm"
                  />
                </div>
              </div>

              <div className="space-y-1.5">
                <label
                  htmlFor={passwordId}
                  className="block text-xs font-medium uppercase tracking-wide text-foreground"
                >
                  Password
                </label>
                <div className="relative">
                  <Lock
                    className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground"
                    aria-hidden="true"
                  />
                  <Input
                    id={passwordId}
                    type={showPassword ? "text" : "password"}
                    name="password"
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    placeholder="At least 8 characters"
                    autoComplete="new-password"
                    required
                    disabled={isLoading}
                    aria-invalid={Boolean(errorMessage)}
                    aria-describedby={errorMessage ? errorId : undefined}
                    className="pl-9 pr-10 text-sm"
                  />
                  <button
                    type="button"
                    onClick={() => setShowPassword((prev) => !prev)}
                    disabled={isLoading}
                    aria-label={showPassword ? "Hide password text" : "Show password text"}
                    className="absolute right-3 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
                  >
                    {showPassword ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                  </button>
                </div>

                {/* Password Strength Indicator */}
                {password.length > 0 && (
                  <div className="space-y-2 pt-1">
                    <div className="flex items-center justify-between text-xs">
                      <span className="text-muted-foreground">Strength:</span>
                      <span className={`font-semibold ${strengthMeta.text}`}>
                        {strengthMeta.label}
                      </span>
                    </div>
                    <div className="grid grid-cols-4 gap-1.5">
                      {[1, 2, 3, 4].map((index) => (
                        <div
                          key={index}
                          className={`h-1.5 rounded-full transition-all duration-300 ${
                            index <= strengthScore ? strengthMeta.color : "bg-muted"
                          }`}
                        />
                      ))}
                    </div>
                    <ul className="space-y-1 text-xs text-muted-foreground">
                      {criteria.map((c, i) => (
                        <li key={i} className="flex items-center gap-1.5">
                          <Check
                            className={`h-3 w-3 ${
                              c.met ? "text-emerald-600" : "text-muted-foreground/40"
                            }`}
                          />
                          <span className={c.met ? "text-foreground font-medium" : ""}>
                            {c.label}
                          </span>
                        </li>
                      ))}
                    </ul>
                  </div>
                )}
              </div>

              <div className="space-y-1.5">
                <label
                  htmlFor={confirmPasswordId}
                  className="block text-xs font-medium uppercase tracking-wide text-foreground"
                >
                  Confirm Password
                </label>
                <div className="relative">
                  <Lock
                    className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground"
                    aria-hidden="true"
                  />
                  <Input
                    id={confirmPasswordId}
                    type={showConfirmPassword ? "text" : "password"}
                    name="confirmPassword"
                    value={confirmPassword}
                    onChange={(e) => setConfirmPassword(e.target.value)}
                    placeholder="Repeat password"
                    autoComplete="new-password"
                    required
                    disabled={isLoading}
                    aria-invalid={Boolean(errorMessage)}
                    aria-describedby={errorMessage ? errorId : undefined}
                    className="pl-9 pr-10 text-sm"
                  />
                  <button
                    type="button"
                    onClick={() => setShowConfirmPassword((prev) => !prev)}
                    disabled={isLoading}
                    aria-label={showConfirmPassword ? "Hide password confirmation" : "Show password confirmation"}
                    className="absolute right-3 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
                  >
                    {showConfirmPassword ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                  </button>
                </div>
              </div>

              {/* Patient Isolation Consent */}
              <div className="flex items-start gap-2.5 pt-1">
                <input
                  id={privacyId}
                  type="checkbox"
                  checked={hasAgreedToPrivacy}
                  onChange={(e) => setHasAgreedToPrivacy(e.target.checked)}
                  disabled={isLoading}
                  className="mt-1 h-4 w-4 rounded border-border text-primary focus:ring-primary"
                  required
                />
                <label htmlFor={privacyId} className="text-xs leading-relaxed text-muted-foreground">
                  I understand that this portal provisions an isolated medical workspace. All
                  clinical documents, chat records, and FHIR bundles are securely linked solely to
                  this account.
                </label>
              </div>

              <Button
                type="submit"
                disabled={isLoading}
                className="w-full h-11 text-sm font-semibold tracking-wide"
              >
                {isLoading ? (
                  <span className="flex items-center justify-center gap-2">
                    <span className="h-4 w-4 animate-spin rounded-full border-2 border-primary-foreground border-t-transparent" />
                    Provisioning account...
                  </span>
                ) : (
                  <span className="flex items-center justify-center gap-2">
                    <span>Complete Registration & Launch</span>
                    <ArrowRight className="h-4 w-4" />
                  </span>
                )}
              </Button>
            </form>

            <footer className="pt-2 text-center text-sm text-muted-foreground">
              Already have an account?{" "}
              <button
                type="button"
                onClick={onSwitchToLogin}
                disabled={isLoading}
                className="font-medium text-primary underline-offset-4 hover:underline focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring rounded-sm"
              >
                Sign in
              </button>
            </footer>
          </div>
        </section>
      </div>
    </main>
  );
};
