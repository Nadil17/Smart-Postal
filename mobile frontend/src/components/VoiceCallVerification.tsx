import { useEffect, useMemo, useRef, useState } from 'react';
import { Phone, PhoneOff, X } from 'lucide-react';
import AudioVisualizer from './AudioVisualizer';
import VoiceStatus from './VoiceStatus';
import { convertBlobToWav } from '../lib/audio/wav';
import {
	getAuthToken,
	loginUser,
	setAuthToken,
	verifyVoiceChallenge,
	verifyVoiceSample,
} from '../lib/api';

export type VoiceCallVerificationProps = {
	recipientName: string;
	orderId?: number;
	onClose: () => void;
	onVerifiedChange?: (verified: boolean) => void;
};

export default function VoiceCallVerification({
	recipientName,
	orderId,
	onClose,
	onVerifiedChange,
}: VoiceCallVerificationProps) {
	const [isCallActive, setIsCallActive] = useState(false);
	const [voiceStatus, setVoiceStatus] = useState<'listening' | 'human' | 'ai'>('listening');
	const [callDuration, setCallDuration] = useState(0);

	const [authEmail, setAuthEmail] = useState('');
	const [authPassword, setAuthPassword] = useState('');
	const [authError, setAuthError] = useState<string | null>(null);

	const [verifyError, setVerifyError] = useState<string | null>(null);
	const [isVerifying, setIsVerifying] = useState(false);
	const [challenge, setChallenge] = useState<{ id: string; phrase: string | null } | null>(null);
	const [verifyMode, setVerifyMode] = useState<'live' | 'upload'>('live');
	const [selectedVerifyFile, setSelectedVerifyFile] = useState<File | null>(null);
	const [selectedChallengeFile, setSelectedChallengeFile] = useState<File | null>(null);

	const audioStreamRef = useRef<MediaStream | null>(null);
	const isMountedRef = useRef(true);

	const hasToken = !!getAuthToken();
	const orderIdNumber = useMemo(() => {
		if (typeof orderId !== 'number') return undefined;
		return Number.isFinite(orderId) ? orderId : undefined;
	}, [orderId]);

	useEffect(() => {
		isMountedRef.current = true;
		return () => {
			isMountedRef.current = false;
			try {
				audioStreamRef.current?.getTracks().forEach((t) => t.stop());
			} catch {
				// ignore
			}
		};
	}, []);

	useEffect(() => {
		let interval: number | undefined;
		if (isCallActive) {
			interval = window.setInterval(() => setCallDuration((prev) => prev + 1), 1000);
			setChallenge(null);
			setVerifyError(null);

			void recordAndVerifyOnce();

			return () => {
				if (interval) clearInterval(interval);
			};
		}

		setCallDuration(0);
		setVoiceStatus('listening');
		setChallenge(null);
		setVerifyError(null);
		setIsVerifying(false);
	}, [isCallActive]);

	useEffect(() => {
		// When switching modes or closing/reopening, clear file selections to avoid accidental re-use.
		setSelectedVerifyFile(null);
		setSelectedChallengeFile(null);
	}, [verifyMode]);

	function formatTime(seconds: number) {
		const mins = Math.floor(seconds / 60);
		const secs = seconds % 60;
		return `${mins}:${secs.toString().padStart(2, '0')}`;
	}

	async function handleBackendAuth(e: React.FormEvent) {
		e.preventDefault();
		setAuthError(null);
		try {
			const res = await loginUser({ email: authEmail, password: authPassword });
			setAuthToken(res.access_token);
		} catch (err: any) {
			setAuthError(err?.message || 'Login failed');
		}
	}

	async function ensureMicStream() {
		if (audioStreamRef.current) return audioStreamRef.current;
		const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
		audioStreamRef.current = stream;
		return stream;
	}

	async function recordAudioBlob(durationMs: number): Promise<Blob> {
		const stream = await ensureMicStream();
		const recorder = new MediaRecorder(stream);
		const chunks: Blob[] = [];
		recorder.ondataavailable = (e) => {
			if (e.data && e.data.size > 0) chunks.push(e.data);
		};

		const stopped = new Promise<Blob>((resolve, reject) => {
			recorder.onstop = () => resolve(new Blob(chunks, { type: recorder.mimeType || 'audio/webm' }));
			recorder.onerror = () => reject(new Error('Recording failed'));
		});

		recorder.start();
		setTimeout(() => {
			try {
				recorder.stop();
			} catch {
				// ignore
			}
		}, durationMs);

		return stopped;
	}

	async function recordAndVerifyOnce() {
		setVerifyError(null);
		setIsVerifying(true);
		setVoiceStatus('listening');
		try {
			const blob = await recordAudioBlob(4000);
			const wavBlob = await convertBlobToWav(blob, 16000);
			const wavFile = new File([wavBlob], `voice_verify_${Date.now()}.wav`, { type: 'audio/wav' });
			const res = await verifyVoiceSample(wavFile, orderIdNumber);

			if (!isMountedRef.current) return;

			if (res.decision === 'CHALLENGE' && res.challenge_id) {
				setChallenge({ id: res.challenge_id, phrase: res.challenge_phrase ?? null });
				setVoiceStatus('listening');
				onVerifiedChange?.(false);
				return;
			}

			const ok = !!res.verified && !res.ai_detected;
			setVoiceStatus(ok ? 'human' : 'ai');
			onVerifiedChange?.(ok);
		} catch (e: any) {
			if (!isMountedRef.current) return;
			setVoiceStatus('ai');
			setVerifyError(e?.message || 'Voice verification failed');
			onVerifiedChange?.(false);
		} finally {
			if (isMountedRef.current) setIsVerifying(false);
		}
	}

	async function uploadAndVerifyOnce(file: File) {
		setVerifyError(null);
		setIsVerifying(true);
		setVoiceStatus('listening');
		try {
			const wavBlob = await convertBlobToWav(file, 16000);
			const wavFile = new File([wavBlob], `voice_verify_upload_${Date.now()}.wav`, { type: 'audio/wav' });
			const res = await verifyVoiceSample(wavFile, orderIdNumber);

			if (!isMountedRef.current) return;

			if (res.decision === 'CHALLENGE' && res.challenge_id) {
				setChallenge({ id: res.challenge_id, phrase: res.challenge_phrase ?? null });
				setVoiceStatus('listening');
				onVerifiedChange?.(false);
				return;
			}

			const ok = !!res.verified && !res.ai_detected;
			setVoiceStatus(ok ? 'human' : 'ai');
			onVerifiedChange?.(ok);
		} catch (e: any) {
			if (!isMountedRef.current) return;
			setVoiceStatus('ai');
			setVerifyError(e?.message || 'Voice verification failed');
			onVerifiedChange?.(false);
		} finally {
			if (isMountedRef.current) setIsVerifying(false);
		}
	}

	async function recordAndVerifyChallenge() {
		if (!challenge) return;
		setVerifyError(null);
		setIsVerifying(true);
		setVoiceStatus('listening');
		try {
			const blob = await recordAudioBlob(5000);
			const wavBlob = await convertBlobToWav(blob, 16000);
			const wavFile = new File([wavBlob], `voice_challenge_${Date.now()}.wav`, { type: 'audio/wav' });
			const res = await verifyVoiceChallenge(challenge.id, wavFile, orderIdNumber);

			if (!isMountedRef.current) return;
			setChallenge(null);
			setVoiceStatus(res.challenge_passed ? 'human' : 'ai');
			onVerifiedChange?.(res.challenge_passed);
		} catch (e: any) {
			if (!isMountedRef.current) return;
			setVoiceStatus('ai');
			setVerifyError(e?.message || 'Challenge verification failed');
			onVerifiedChange?.(false);
		} finally {
			if (isMountedRef.current) setIsVerifying(false);
		}
	}

	async function uploadAndVerifyChallenge(file: File) {
		if (!challenge) return;
		setVerifyError(null);
		setIsVerifying(true);
		setVoiceStatus('listening');
		try {
			const wavBlob = await convertBlobToWav(file, 16000);
			const wavFile = new File([wavBlob], `voice_challenge_upload_${Date.now()}.wav`, { type: 'audio/wav' });
			const res = await verifyVoiceChallenge(challenge.id, wavFile, orderIdNumber);

			if (!isMountedRef.current) return;
			setChallenge(null);
			setVoiceStatus(res.challenge_passed ? 'human' : 'ai');
			onVerifiedChange?.(res.challenge_passed);
		} catch (e: any) {
			if (!isMountedRef.current) return;
			setVoiceStatus('ai');
			setVerifyError(e?.message || 'Challenge verification failed');
			onVerifiedChange?.(false);
		} finally {
			if (isMountedRef.current) setIsVerifying(false);
		}
	}

	return (
		<div className="fixed inset-0 z-[60] flex items-center justify-center">
			<div className="absolute inset-0 bg-black/60" onClick={() => !isVerifying && onClose()} />
			<div className="relative z-10 w-full max-w-md mx-4 rounded-2xl bg-gray-900 text-white border border-white/10 overflow-hidden">
				<div className="p-4 flex items-center justify-between border-b border-white/10">
					<div>
						<div className="text-sm text-gray-300">Call & Verify Voice</div>
						<div className="text-lg font-semibold">{recipientName}</div>
					</div>
					<button className="p-2 rounded-lg hover:bg-white/10" onClick={() => !isVerifying && onClose()} aria-label="Close">
						<X size={20} />
					</button>
				</div>

				<div className="p-5">
					<div className="flex items-center justify-between">
						<div className="text-sm text-gray-400">{isCallActive ? formatTime(callDuration) : 'Ready'}</div>
						{hasToken && (
							<button
								className="text-xs text-gray-300 hover:text-white"
								onClick={() => {
									setAuthToken(null);
									setAuthEmail('');
									setAuthPassword('');
									setAuthError(null);
								}}
							>
								Sign out
							</button>
						)}
					</div>

					{!hasToken && !isCallActive && (
						<div className="mt-4 bg-white/10 backdrop-blur-md rounded-2xl p-4 border border-white/10">
							<h2 className="font-semibold mb-3">Sign in</h2>
							<form onSubmit={handleBackendAuth} className="flex flex-col gap-3">
								<input
									type="email"
									value={authEmail}
									onChange={(e) => setAuthEmail(e.target.value)}
									placeholder="Email"
									className="w-full px-3 py-2 rounded-lg bg-black/20 border border-white/10 focus:outline-none"
									required
								/>
								<input
									type="password"
									value={authPassword}
									onChange={(e) => setAuthPassword(e.target.value)}
									placeholder="Password"
									className="w-full px-3 py-2 rounded-lg bg-black/20 border border-white/10 focus:outline-none"
									required
								/>
								{authError && <div className="text-sm text-red-300">{authError}</div>}
								<button type="submit" className="w-full py-2 rounded-lg bg-blue-600 hover:bg-blue-700 font-semibold">
									Sign In
								</button>
							</form>
						</div>
					)}

					{(hasToken || isCallActive) && (
						<div className="mt-4 bg-white/10 backdrop-blur-md rounded-2xl p-5 border border-white/10">
							<div className="flex gap-2">
								<button
									type="button"
									onClick={() => setVerifyMode('live')}
									className={`flex-1 py-2 rounded-lg text-sm font-semibold border border-white/10 ${
										verifyMode === 'live' ? 'bg-white/10' : 'bg-transparent hover:bg-white/5'
									}`}
								>
									Live (Mic)
								</button>
								<button
									type="button"
									onClick={() => setVerifyMode('upload')}
									className={`flex-1 py-2 rounded-lg text-sm font-semibold border border-white/10 ${
										verifyMode === 'upload' ? 'bg-white/10' : 'bg-transparent hover:bg-white/5'
									}`}
								>
								Manual (Upload)
								</button>
							</div>

							<VoiceStatus status={voiceStatus} />
							<div className="mt-4">
								<AudioVisualizer isActive={isCallActive || isVerifying} isAiDetected={voiceStatus === 'ai'} />
							</div>
							{verifyError && <div className="mt-3 text-sm text-red-300">{verifyError}</div>}

							{verifyMode === 'upload' && !challenge && (
								<div className="mt-4">
									<label className="block text-xs text-gray-300 mb-2">Upload verification audio</label>
									<input
										type="file"
										accept="audio/*"
										onChange={(e) => setSelectedVerifyFile(e.target.files?.[0] ?? null)}
										className="block w-full text-sm text-gray-200 file:mr-3 file:py-2 file:px-3 file:rounded-lg file:border-0 file:bg-white/10 file:text-gray-100 hover:file:bg-white/15"
									/>
									<button
										type="button"
										disabled={isVerifying || !selectedVerifyFile}
										onClick={() => selectedVerifyFile && void uploadAndVerifyOnce(selectedVerifyFile)}
										className="mt-3 w-full py-2 rounded-lg bg-blue-600 hover:bg-blue-700 disabled:opacity-60 font-semibold"
									>
										{isVerifying ? 'Verifying…' : 'Verify Uploaded Audio'}
									</button>
								</div>
							)}

							{challenge && (
								<div className="mt-4 p-4 rounded-xl bg-yellow-500/10 border border-yellow-500/20">
									<div className="text-sm text-yellow-200 font-medium">Liveness challenge required</div>
									{challenge.phrase && <div className="mt-2 text-sm text-yellow-100">Say: “{challenge.phrase}”</div>}

									{verifyMode === 'upload' ? (
										<>
											<label className="block text-xs text-gray-300 mt-3 mb-2">Upload challenge response</label>
											<input
												type="file"
												accept="audio/*"
												onChange={(e) => setSelectedChallengeFile(e.target.files?.[0] ?? null)}
												className="block w-full text-sm text-gray-200 file:mr-3 file:py-2 file:px-3 file:rounded-lg file:border-0 file:bg-white/10 file:text-gray-100 hover:file:bg-white/15"
											/>
											<button
												type="button"
												disabled={isVerifying || !selectedChallengeFile}
												onClick={() => selectedChallengeFile && void uploadAndVerifyChallenge(selectedChallengeFile)}
												className="mt-3 w-full py-2 rounded-lg bg-yellow-600 hover:bg-yellow-700 disabled:opacity-60 font-semibold"
											>
												{isVerifying ? 'Verifying…' : 'Verify Uploaded Challenge Audio'}
											</button>
										</>
									) : (
										<button
											type="button"
											onClick={() => void recordAndVerifyChallenge()}
											disabled={isVerifying}
											className="mt-3 w-full py-2 rounded-lg bg-yellow-600 hover:bg-yellow-700 disabled:opacity-60 font-semibold"
										>
											{isVerifying ? 'Recording…' : 'Record Challenge Response'}
										</button>
									)}
								</div>
							)}
						</div>
					)}
				</div>

				<div className="p-6 flex justify-center items-center gap-6 bg-gray-900/50 border-t border-white/10">
					{isCallActive ? (
						<button
							onClick={() => setIsCallActive(false)}
							className="w-16 h-16 bg-red-500 rounded-full flex items-center justify-center shadow-lg hover:bg-red-600 transition-transform active:scale-95"
							aria-label="End call"
						>
							<PhoneOff size={32} />
						</button>
					) : (
						<button
							type="button"
							onClick={() => {
								if (!getAuthToken()) {
									setAuthError('Please sign in first');
									return;
								}
								if (verifyMode === 'upload') {
									setVerifyError('Use the upload button above to verify.');
									return;
								}
								setIsCallActive(true);
							}}
							disabled={isVerifying}
							className="w-16 h-16 bg-green-500 rounded-full flex items-center justify-center shadow-lg hover:bg-green-600 transition-transform active:scale-95 disabled:opacity-60"
							aria-label="Start call"
						>
							<Phone size={32} />
						</button>
					)}
				</div>
			</div>
		</div>
	);
}
