# System Mechanics & Dependencies Explained

## 1. How the Dependencies Work

The backend relies on a specific stack of libraries to perform "Banking-Grade" security. Here is the functional role of each key library:

### Core Frameworks
*   **FastAPI**: The asynchronous web server. It handles HTTP requests (like `/enroll` and `/verify`) without blocking, which is critical because audio processing is CPU-intensive.
*   **Torch (PyTorch)**: The deep learning engine. It powers the neural networks used for voice embedding generation.

### Audio Intelligence
*   **Librosa**: The "Swiss Army Knife" for audio. We use it to load audio files and extract raw acoustic features:
    *   *MFCCs (Mel-frequency cepstral coefficients)*: To capture the unique "timbre" of the voice.
    *   *Spectral Centroid*: To analyze the "brightness" of the sound (helps detect AI voices which are often "duller" in high frequencies).
    *   *Zero-Crossing Rate*: To detect unnatural silence/continuity typical of synthesized speech.
*   **Resemblyzer**: A specialized library that takes a voice clip and converts it into a **256-dimensional vector** (called a d-vector or embedding). This vector is the mathematical "fingerprint" of the voice. Two recordings of the same person will have vectors that are numerically very close.
*   **SciPy**: Used for advanced signal processing, specifically to calculate statistical metrics like **Kurtosis** and **Skewness** of the audio energy. Real human voices have chaotic energy fluctuations; AI voices are often statistically "too perfect," which SciPy helps detect.

---

## 2. Workflows Explained

### A. How Enrollment Works
The goal of enrollment is to create a secure, trusted "Master Template."

1.  **Frontend Capture**:
    *   User records voice samples (e.g., "My name is John") via `VoiceEnroller.tsx`.
    *   Audio is uploaded to `POST /api/voice/enroll`.
2.  **Backend Processing**:
    *   **Quality Check**: Ensures audio is not too quiet (SNR) or too short.
    *   **Anti-Spoofing (Strict)**: `anti_spoof.py` analyzes the audio for synthetic artifacts (e.g., consistent formants, lack of breathing). If it looks like AI, it is rejected immediately.
    *   **Vectorization**: `Resemblyzer` converts the audio into an embedding.
3.  **Storage**:
    *   The embedding is encrypted and sequestered in the `voice_templates` database table.
    *   Multiple samples are averaged to create a robust mean vector.

### B. How Verification Works
The goal is to answer: "Is this the enrolled user?" AND "Is this a live human?"

1.  **Identity Matching (The "Who")**:
    *   The system loads the user's stored Master Template.
    *   It generates a new embedding for the incoming audio.
    *   It calculates **Cosine Similarity** (a score from 0.0 to 1.0).
2.  **Liveness Detection (The "What")**:
    *   **Spectral Gating**: Checks for background noise floors (silence = suspicious).
    *   **Replay Detection**: Checks for echoes indicating the audio was played over a speaker.
    *   **AI Probability**: If the AI score is > 60%, the request is blocked.
3.  **Risk-Based Decision**:
    *   **Accept**: High Similarity + Low AI Risk.
    *   **Challenge**: High Similarity but Medium AI Risk (or first-time device). The system triggers a "Liveness Challenge," requiring the user to speak a random code (e.g., "4-9-2-1").
    *   **Deny**: Low Similarity or Critical AI Risk.
