# Smart Postal - Voice Authentication System

## 1. Project Overview

The **Smart Postal Voice Authentication System** is a "Banking-Grade" biometric security module designed to secure high-value deliveries. It ensures that only the verified recipient can accept a package by using advanced voice biometrics.

Key capabilities include:
-   **Voice Enrollment**: Captures user voice to create a secure biometric template.
-   **Voice Verification**: Verifies identity during delivery handling or checkout.
-   **AI & Synthetic Voice Detection**: Uses advanced spectral and temporal analysis to detect deepfakes, TTS (Text-to-Speech), and voice cloners.
-   **Active Liveness Detection**: Challenges users to speak random phrases to prevent replay attacks.
-   **Adaptive Learning**: Updates voice templates over time to account for aging and minor voice changes.

## 2. System Architecture

The system follows a tiered architecture separating the mobile frontend from the secure biometric backend.

```mermaid
graph TD
    subgraph "Mobile Frontend"
        UI[User Interface (React)]
        Rec[Audio Recorder]
        Enroller[VoiceEnroller.tsx]
        Verifier[VoiceCallVerification.tsx]
    end

    subgraph "Backend API (FastAPI)"
        API[Voice Routes (voice.py)]
        Auth[Authentication Layer]
    end

    subgraph "Biometric Core"
        Processor[BankingGrade Voice Processor]
        AntiSpoof[Anti-Spoofing Engine]
        Decision[Risk-Based Decision Engine]
        Models[Resemblyzer / PyTorch]
    end

    subgraph "Data Store"
        DB[(Database)]
        Templates[Voice Templates]
        Logs[Verification Logs]
    end

    Rec --> UI
    UI -->|Upload Audio| API
    API -->|Process| Processor
    Processor -->|Check Liveness| AntiSpoof
    Processor -->|Extract Features| Models
    Processor -->|Evaluate| Decision
    Decision -->|RW Encrypted Data| DB
```

### Core Components
1.  **Frontend**:
    -   **VoiceEnroller**: Handles the multi-sample recording process for creating a robust voice profile.
    -   **VoiceCallVerification**: Simulates a secured call for real-time verification, supporting "Challenge-Response" flows.
2.  **Backend**:
    -   **Voice Processor (`voice_banking.py`)**: The heart of the system. It handles noise reduction, audio enhancement, and runs the ensemble verification logic.
    -   **Anti-Spoofing (`anti_spoof.py`)**: Analyzes audio for artifacts typical of AI generation (perfect pitch, lack of breathing, spectral inconsistencies).
    -   **Decision Engine**: Calculates a composite risk score based on AI probability, speaker similarity (ASV), and metadata to automatically Accept, Challenge, or Deny.

## 3. Project Dependencies

### Backend (Python)
The backend requires a Python environment (3.8+) with the following key libraries:

*   **FastAPI**: High-performance web framework.
*   **Torch (PyTorch) & Torchaudio**: Deep learning framework for biometric models.
*   **Resemblyzer**: For extracting high-dimensional voice embeddings.
*   **Librosa**: For audio processing and feature extraction (MFCC, Spectral data).
*   **NumPy & SciPy**: specific mathematical operations for signal processing.
*   **SQLAlchemy**: ORM for database interactions.
*   **Loguru**: Enhanced logging.

### Frontend (TypeScript/React)
The mobile frontend is built with React/React Native technologies:

*   **React**: UI Library.
*   **Lucide React**: Iconography.
*   **TailwindCSS**: Styling (via `clsx` for dynamic classes).
*   **MediaStream API**: Native browser API for capturing audio.

## 4. Security Features

*   **Deepfake Detection**: Analyzes 10+ acoustic features (MFCC variance, Energy Kurtosis, Phase Coherence) to flag synthetic voices.
*   **Re-recording Detection**: Detects echoes and band-limiting residue from playing a recording over a speaker.
*   **Challenge-Response**: If risk is elevated (Medium/High), the system generates a dynamic phrase (e.g., "Confirm by saying: 8392") that the user must speak instantly.

## 5. Setup & Usage

1.  **Enrollment**:
    -   Navigate to Checkout.
    -   Complete the "Voice Security Enrollment" by recording your voice 3 times.
2.  **Verification**:
    -   Initiate a voice verification call.
    -   Speak naturally or follow the challenge instructions.
    -   The system will provide real-time feedback: "Human Verified", "AI Detected", or "Liveness Challenge Required".
