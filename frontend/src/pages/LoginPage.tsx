import { useMutation } from '@tanstack/react-query'
import { ArrowLeft, KeyRound } from 'lucide-react'
import { useEffect, useState, type FormEvent } from 'react'
import { Link, useNavigate, useSearchParams } from 'react-router'

import { Logo } from '../components/layout'
import { Button } from '../components/ui'
import { api, messageOf } from '../lib/api'
import { formatPhone } from '../lib/format'
import { useUpdateProfile } from '../lib/queries'
import type { OtpRequestResult, Session } from '../lib/types'
import { isStaff, useAuth } from '../store/auth'
import { toast } from '../store/toast'

const DEMO_ACCOUNTS = [
  { phone: '9876543210', label: 'Demo customer', hint: 'has a saved address' },
  { phone: '9000000001', label: 'Store staff', hint: 'Sector 29 store' },
  { phone: '9999999999', label: 'Admin', hint: 'all stores' },
]

function safeNext(value: string | null): string {
  return value && value.startsWith('/') && !value.startsWith('//') ? value : '/'
}

export default function LoginPage() {
  const navigate = useNavigate()
  const [params] = useSearchParams()
  const next = safeNext(params.get('next'))
  const setSession = useAuth((s) => s.setSession)

  const [step, setStep] = useState<'phone' | 'otp' | 'name'>('phone')
  const [phone, setPhone] = useState('')
  const [otp, setOtp] = useState('')
  const [name, setName] = useState('')
  const [sent, setSent] = useState<OtpRequestResult | null>(null)
  const [resendIn, setResendIn] = useState(0)

  useEffect(() => {
    if (resendIn <= 0) return
    const timer = window.setTimeout(() => setResendIn((s) => s - 1), 1000)
    return () => window.clearTimeout(timer)
  }, [resendIn])

  const requestOtp = useMutation({
    mutationFn: (value: string) => api<OtpRequestResult>('/auth/otp/request', { body: { phone: value } }),
    onSuccess: (result) => {
      setSent(result)
      setPhone(result.phone)
      setOtp('')
      setResendIn(result.resend_in)
      setStep('otp')
    },
    onError: (error) => toast(messageOf(error), 'error'),
  })

  const finish = (redirectTo: string) => navigate(redirectTo, { replace: true })

  const verify = useMutation({
    mutationFn: (code: string) => api<Session>('/auth/otp/verify', { body: { phone, otp: code } }),
    onSuccess: (session) => {
      setSession(session.access_token, session.user)
      toast(session.is_new_user ? 'Welcome to Smart Cart!' : 'Welcome back!', 'success')
      if (!session.user.name) setStep('name')
      else finish(next === '/' && isStaff(session.user) ? '/staff' : next)
    },
    onError: (error) => {
      setOtp('')
      toast(messageOf(error), 'error')
    },
  })

  const saveName = useUpdateProfile()

  const submitPhone = (event: FormEvent) => {
    event.preventDefault()
    requestOtp.mutate(phone)
  }
  const submitOtp = (event?: FormEvent) => {
    event?.preventDefault()
    if (otp.length >= 4) verify.mutate(otp)
  }

  return (
    <div className="flex min-h-[calc(100dvh-var(--header-h))] items-start justify-center px-4 py-8">
      <div className="w-full max-w-sm rounded-3xl bg-white p-6 shadow-sm ring-1 ring-black/5">
        <div className="mb-6 flex flex-col items-center text-center">
          <Logo />
          <h1 className="mt-4 text-2xl font-extrabold">
            {step === 'phone' ? 'Log in or sign up' : step === 'otp' ? 'Enter verification code' : 'What should we call you?'}
          </h1>
          <p className="mt-1 text-sm text-gray-500">
            {step === 'phone' && 'Groceries in minutes, pickup on your schedule, and in-store help.'}
            {step === 'otp' && `We sent a ${sent?.dev_otp?.length ?? 6}-digit code to ${formatPhone(phone)}`}
            {step === 'name' && 'So the store knows who is picking up.'}
          </p>
        </div>

        {step === 'phone' && (
          <form onSubmit={submitPhone} className="space-y-4">
            <label className="flex h-12 items-center rounded-xl border border-gray-300 bg-white px-3 focus-within:border-brand-600 focus-within:ring-2 focus-within:ring-brand-100">
              <span className="mr-2 border-r border-gray-200 pr-2 font-semibold text-gray-600">+91</span>
              <input
                autoFocus
                inputMode="numeric"
                autoComplete="tel-national"
                value={phone}
                onChange={(e) => setPhone(e.target.value.replace(/\D/g, '').slice(0, 10))}
                placeholder="Enter mobile number"
                className="h-full min-w-0 flex-1 bg-transparent text-lg tracking-wider outline-none placeholder:text-base placeholder:tracking-normal"
                aria-label="Mobile number"
              />
            </label>
            <Button type="submit" block className="h-12 text-base" loading={requestOtp.isPending} disabled={phone.length !== 10}>
              Continue
            </Button>
            <div className="rounded-2xl bg-gray-50 p-3">
              <p className="mb-2 text-xs font-bold uppercase tracking-wider text-gray-500">Demo accounts</p>
              <div className="space-y-1.5">
                {DEMO_ACCOUNTS.map((account) => (
                  <button
                    key={account.phone}
                    type="button"
                    onClick={() => setPhone(account.phone)}
                    className="flex w-full items-center justify-between rounded-lg bg-white px-3 py-2 text-left text-sm ring-1 ring-black/5 hover:ring-brand-300"
                  >
                    <span>
                      <span className="font-semibold">{account.label}</span>
                      <span className="block text-xs text-gray-500">{account.hint}</span>
                    </span>
                    <span className="font-mono text-xs text-gray-500">{account.phone}</span>
                  </button>
                ))}
              </div>
            </div>
          </form>
        )}

        {step === 'otp' && (
          <form onSubmit={submitOtp} className="space-y-4">
            <input
              autoFocus
              inputMode="numeric"
              autoComplete="one-time-code"
              value={otp}
              onChange={(e) => {
                const value = e.target.value.replace(/\D/g, '').slice(0, 6)
                setOtp(value)
                if (value.length === 6) verify.mutate(value)
              }}
              placeholder="••••••"
              className="h-14 w-full rounded-xl border border-gray-300 text-center font-mono text-3xl tracking-[0.5em] outline-none focus:border-brand-600 focus:ring-2 focus:ring-brand-100"
              aria-label="One-time password"
            />
            {sent?.dev_otp && (
              <button
                type="button"
                onClick={() => {
                  setOtp(sent.dev_otp!)
                  verify.mutate(sent.dev_otp!)
                }}
                className="flex w-full items-center justify-center gap-2 rounded-xl bg-amber-50 px-3 py-2.5 text-sm text-amber-800 ring-1 ring-amber-200"
              >
                <KeyRound className="size-4" />
                Dev mode: your code is <b className="font-mono tracking-widest">{sent.dev_otp}</b> · tap to use
              </button>
            )}
            <Button type="submit" block className="h-12 text-base" loading={verify.isPending} disabled={otp.length < 4}>
              Verify & continue
            </Button>
            <div className="flex items-center justify-between text-sm">
              <button type="button" onClick={() => setStep('phone')} className="flex items-center gap-1 font-semibold text-gray-600">
                <ArrowLeft className="size-4" /> Change number
              </button>
              <button
                type="button"
                disabled={resendIn > 0 || requestOtp.isPending}
                onClick={() => requestOtp.mutate(phone)}
                className="font-semibold text-brand-700 disabled:text-gray-400"
              >
                {resendIn > 0 ? `Resend in ${resendIn}s` : 'Resend code'}
              </button>
            </div>
          </form>
        )}

        {step === 'name' && (
          <form
            onSubmit={(event) => {
              event.preventDefault()
              if (!name.trim()) return finish(next)
              saveName.mutate({ name: name.trim() }, { onSettled: () => finish(next) })
            }}
            className="space-y-4"
          >
            <input
              autoFocus
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="Your name"
              maxLength={80}
              className="h-12 w-full rounded-xl border border-gray-300 px-4 text-lg outline-none focus:border-brand-600 focus:ring-2 focus:ring-brand-100"
              aria-label="Your name"
            />
            <Button type="submit" block className="h-12 text-base" loading={saveName.isPending}>
              {name.trim() ? 'Save & continue' : 'Skip for now'}
            </Button>
          </form>
        )}

        <p className="mt-6 text-center text-xs text-gray-400">
          By continuing you agree to our terms of service & privacy policy. <Link to="/" className="underline">Back to shop</Link>
        </p>
      </div>
    </div>
  )
}
