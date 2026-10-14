import {
  AlertCircle,
  ArrowRight,
  Eye,
  EyeOff,
  HeartPulse,
  KeyRound,
  Lock,
  Mail,
  ShieldCheck,
  Sparkles,
} from "lucide-react";
import React, { useId, useState } from "react";
import { useAuth } from "../../context/AuthContext";
import { Button } from "../ui/button";
import { Input } from "../ui/input";

interface LoginPageProps {
  onSwitchToRegister: () => void;
}

export const LoginPage: React.FC<LoginPageProps> = ({ onSwitchToRegister }) => {
  const { login } = useAuth();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [isDemoLoading, setIsDemoLoading] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  const emailId = useId();
  const passwordId = useId();
  const errorId = useId();

  async function handleLogin(e: React.FormEvent) {
    e.preventDefault();
    setErrorMessage(null);

    const cleanEmail = email.trim();
    if (!cleanEmail) {
      setErrorMessage("Please enter your email address.");
      return;
    }
    if (!password) {
      setErrorMessage("Please enter your password.");
      return;
    }

    setIsLoading(true);
    try {
      await login({ email: cleanEmail, password });
    } catch (err: unknown) {
      const msg =
        err instanceof Error
          ? err.message
          : "Authentication failed. Please verify your credentials.";
      setErrorMessage(msg);
    } finally {
      setIsLoading(false);
    }
  }

  async function handleDemoLogin() {
    setErrorMessage(null);
    setIsDemoLoading(true);
    // Real authentication through backend using configured synthetic demo account
    try {
      await login({
        email: "demo@healthcopilot.local",
        password: "Demo@2026",
      });
    } catch (err: unknown) {
      const msg =
        err instanceof Error
          ? err.message
          : "Could not authenticate demo account. Please ensure the backend server is running.";
      setErrorMessage(msg);
    } finally {
      setIsDemoLoading(false);
    }
  }

  return (
    <main className="flex min-h-screen items-center justify-center bg-background px-4 py-8 sm:px-6 lg:px-8">
      <div className="w-full max-w-5xl overflow-hidden rounded-2xl border border-border bg-card shadow-xl lg:grid lg:grid-cols-12">
        {/* Left Clinical Brand Showcase */}
        <section
          aria-label="Personal Health Copilot Features"
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
                Verified Patient Isolation
              </span>
              <h2 className="font-display text-2xl font-medium leading-snug sm:text-3xl">
                Continuous clinical intelligence, strictly isolated to your care.
              </h2>
              <p className="text-sm leading-relaxed text-primary-foreground/80">
                Securely persist medical documents, query comprehensive patient history with
                grounded AI citations, and generate bilingual Telugu summaries with full HIPAA-grade
                patient ownership.
              </p>
            </div>

            <ul className="space-y-3.5 pt-4 text-xs sm:text-sm text-primary-foreground/90">
              <li className="flex items-center gap-2.5">
                <ShieldCheck className="h-4 w-4 shrink-0 text-emerald-300" />
                <span>Zero-trust patient isolation & JWT encrypted sessions</span>
              </li>
              <li className="flex items-center gap-2.5">
                <ShieldCheck className="h-4 w-4 shrink-0 text-emerald-300" />
                <span>Multimodal PDF text extraction & OCR vision pipeline</span>
              </li>
              <li className="flex items-center gap-2.5">
                <ShieldCheck className="h-4 w-4 shrink-0 text-emerald-300" />
                <span>HL7 FHIR R4 standard clinical bundle interoperability</span>
              </li>
            </ul>
          </div>

          <div className="mt-8 border-t border-primary-foreground/15 pt-6 text-xs text-primary-foreground/75">
            <p>Clinical data is stored strictly in your dedicated tenancy.</p>
          </div>
        </section>

        {/* Right Authentication Form */}
        <section
          aria-label="Sign In Form"
          className="flex flex-col justify-center p-6 sm:p-10 lg:col-span-7"
        >
          <div className="mx-auto w-full max-w-md space-y-6">
            <header className="space-y-1.5">
              <h1 className="font-display text-2xl font-semibold tracking-tight text-foreground sm:text-3xl">
                Sign in to your portal
              </h1>
              <p className="text-sm text-muted-foreground">
                Enter your credentials to securely access your medical workspace.
              </p>
            </header>

            {/* Quick Demo Access Action */}
            <div className="rounded-xl border border-primary/20 bg-accent/40 p-4 transition-all hover:border-primary/40">
              <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
                <div>
                  <div className="flex items-center gap-1.5 text-xs font-semibold uppercase tracking-wider text-primary">
                    <KeyRound className="h-3.5 w-3.5" />
                    <span>Evaluation Mode</span>
                  </div>
                  <p className="mt-0.5 text-xs text-muted-foreground">
                    Try with pre-seeded synthetic patient data (Smt. Sunita Rao).
                  </p>
                </div>
                <Button
                  type="button"
                  size="sm"
                  variant="outline"
                  disabled={isLoading || isDemoLoading}
                  onClick={handleDemoLogin}
                  className="shrink-0 font-medium"
                >
                  {isDemoLoading ? (
                    <span className="flex items-center gap-1.5">
                      <span className="h-3 w-3 animate-spin rounded-full border-2 border-primary border-t-transparent" />
                      Authenticating...
                    </span>
                  ) : (
                    "Try Demo Account"
                  )}
                </Button>
              </div>
            </div>

            <div className="relative flex items-center justify-center">
              <div className="w-full border-t border-border" />
              <span className="absolute bg-card px-3 text-xs font-medium uppercase tracking-wider text-muted-foreground">
                or sign in with credentials
              </span>
            </div>

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
                  <p className="font-medium">Authentication Failed</p>
                  <p className="mt-0.5 text-xs leading-relaxed text-red-700">{errorMessage}</p>
                </div>
              </div>
            ) : null}

            <form onSubmit={handleLogin} className="space-y-4" noValidate>
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
                    placeholder="doctor@hospital.org or patient@domain.com"
                    autoComplete="email"
                    required
                    disabled={isLoading || isDemoLoading}
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
                    placeholder="••••••••"
                    autoComplete="current-password"
                    required
                    disabled={isLoading || isDemoLoading}
                    aria-invalid={Boolean(errorMessage)}
                    aria-describedby={errorMessage ? errorId : undefined}
                    className="pl-9 pr-10 text-sm"
                  />
                  <button
                    type="button"
                    onClick={() => setShowPassword((prev) => !prev)}
                    disabled={isLoading || isDemoLoading}
                    aria-label={showPassword ? "Hide password text" : "Show password text"}
                    className="absolute right-3 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
                  >
                    {showPassword ? (
                      <EyeOff className="h-4 w-4" />
                    ) : (
                      <Eye className="h-4 w-4" />
                    )}
                  </button>
                </div>
              </div>

              <Button
                type="submit"
                disabled={isLoading || isDemoLoading}
                className="w-full h-11 text-sm font-semibold tracking-wide"
              >
                {isLoading ? (
                  <span className="flex items-center justify-center gap-2">
                    <span className="h-4 w-4 animate-spin rounded-full border-2 border-primary-foreground border-t-transparent" />
                    Verifying session...
                  </span>
                ) : (
                  <span className="flex items-center justify-center gap-2">
                    <span>Sign In to Health Portal</span>
                    <ArrowRight className="h-4 w-4" />
                  </span>
                )}
              </Button>
            </form>

            <footer className="pt-2 text-center text-sm text-muted-foreground">
              Don&apos;t have an account yet?{" "}
              <button
                type="button"
                onClick={onSwitchToRegister}
                disabled={isLoading || isDemoLoading}
                className="font-medium text-primary underline-offset-4 hover:underline focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring rounded-sm"
              >
                Create account
              </button>
            </footer>

            <div className="rounded-lg bg-muted/60 p-3 text-center text-xs leading-5 text-muted-foreground">
              <ShieldCheck className="mr-1 inline-block h-3.5 w-3.5 text-primary" />
              <span>
                Protected under JWT authentication & patient-level cryptographic authorization.
              </span>
            </div>
          </div>
        </section>
      </div>
    </main>
  );
};
