# 🧪 Quick Testing Guide

## Server Status
✅ **Server Running**: `http://localhost:8000`

## What's New?
🔊 **Noise reduction** automatically applied  
🌍 **Works outdoors** and in noisy environments  
📉 **Relaxed thresholds** (0.72 ensemble, 0.60 cosine)  
🛡️ **Lenient liveness** (fail-open approach)  

---

## Test Steps

### 1. **Login**
```bash
POST /api/auth/login
{
  "username": "your_username",
  "password": "your_password"
}
```
Save the `access_token`

### 2. **Enroll Voice** (Try Outdoors!)
```bash
POST /api/voice/enroll
Headers: Authorization: Bearer <token>
Body: FormData with 3+ audio files
```

**Expected**: Should accept even with background noise (SNR ≥3dB)

### 3. **Verify Voice** (Different Environment)
```bash
POST /api/voice/verify
Headers: Authorization: Bearer <token>
Body: FormData with audio file
```

**Expected**: 
- ✅ **Cosine ≥0.60** → Pass
- ✅ **Ensemble ≥0.72** → Verified
- ✅ **Liveness**: Usually passes (fail-open)

---

## Expected Scores

### ✅ Good Match (Same Person):
```json
{
  "verified": true,
  "ensemble_score": 0.75-0.90,
  "cosine_similarity": 0.65-0.92,
  "euclidean_score": 0.70-0.85,
  "correlation_score": 0.60-0.80
}
```

### ❌ Different Person:
```json
{
  "verified": false,
  "ensemble_score": 0.40-0.65,
  "cosine_similarity": 0.30-0.55,
  "euclidean_score": 0.50-0.70,
  "correlation_score": 0.30-0.60
}
```

---

## Testing Scenarios

### ✅ Should Work Now:
- [ ] **Outdoor recording** (wind, traffic)
- [ ] **Noisy indoor** (TV, conversations)
- [ ] **Different microphones** (laptop vs phone)
- [ ] **Varying distances** (near vs far from mic)
- [ ] **Lower quality audio** (SNR 3-8dB)

### ❌ Should Still Reject:
- [ ] **Different speaker** (someone else's voice)
- [ ] **Extremely noisy** (SNR < 3dB)
- [ ] **Too short** (< 0.5 seconds)
- [ ] **Completely synthetic** (zero energy variance)

---

## Debug Tips

### Check Quality Metrics:
```json
"quality_metrics": {
  "snr": 5.2,           // ≥3.0 required
  "duration": 2.5,      // 0.5-60s required
  "spectral_flatness": 0.45,  // ≤0.95 required
  "is_acceptable": true
}
```

### Check Liveness (If Enabled):
```json
"liveness_metrics": {
  "confidence": 0.9,    // Usually high now
  "is_live": true       // Defaults to true (fail-open)
}
```

### Check Verification:
```json
"ensemble_score": 0.78,        // ≥0.72 needed
"cosine_similarity": 0.72,     // ≥0.60 needed (critical!)
"threshold_used": 0.72,
"min_cosine_threshold": 0.60
```

---

## If It Still Fails...

### 1. **Check Server Logs**
Look for:
- `📊 Quality: SNR=X.XdB` (should be ≥3.0)
- `✓ Enhanced embedding extracted` (noise reduction worked)
- `🔍 Verification: Ensemble=X.XX, Cosine=X.XX`

### 2. **Adjust Thresholds** (if needed)
Edit `config/settings.py`:
```python
VOICE_SIMILARITY_THRESHOLD = 0.70  # Lower if rejecting same person
LIVENESS_THRESHOLD = 0.15          # Lower if liveness fails
```

### 3. **Try Re-enrollment**
- Use 3+ high-quality samples
- Record in moderate environment (not complete silence)
- Speak clearly for 1-3 seconds each

### 4. **Disable Liveness** (last resort)
Edit `api/routes/voice.py`:
```python
# Line ~145 in verify endpoint
perform_liveness_check=False  # Was: True
```

---

## API Endpoints

### Authentication:
- `POST /api/auth/register` - Create account
- `POST /api/auth/login` - Get token

### Voice:
- `POST /api/voice/enroll` - Enroll voice (3+ samples)
- `POST /api/voice/verify` - Verify identity
- `GET /api/voice/status/{user_id}` - Check enrollment status

### Testing:
- `GET /health` - Server health check
- `GET /` - API info

---

## Frontend Testing

Open `frontend_test/index.html` in browser:

1. **Login** with credentials
2. **Enroll** - Upload 3 audio files (can be noisy!)
3. **Verify** - Upload test audio
4. **Check results** - See detailed metrics

Look for:
- 🔍 Quality assessment
- 🛡️ Liveness check  
- 📊 Verification scores
- ✅ Final result

---

## Noise Reduction Testing

Record audio in **noisy environment**, check logs:
```
✓ Enhanced embedding extracted: shape=(256,)
```
This means noise reduction worked!

If you see:
```
⚠️ Enhancement failed, using original: ...
```
Noise reduction failed, but still works (fallback to original).

---

## Performance Expectations

### Enrollment:
- Time: ~2-5 seconds (3 samples)
- Quality: Accepts SNR ≥3dB
- Liveness: **Disabled** (lenient enrollment)

### Verification:
- Time: ~1-2 seconds per attempt
- Quality: Accepts SNR ≥3dB + noise reduction
- Liveness: **Enabled but lenient** (fail-open)
- Threshold: 0.72 ensemble, 0.60 cosine

---

## Success Criteria

✅ **System Working If**:
- Can enroll outdoors with background noise
- Can verify from different environment
- Same person: ensemble ≥0.72, cosine ≥0.60
- Different person: Rejected (scores <0.60)

---

## Questions?

Check documentation:
- `REAL_WORLD_ENHANCEMENTS.md` - Technical details
- `VOICE_VERIFICATION_BANKING_GRADE.md` - Original design
- Server logs - Detailed metrics

**Happy Testing! 🚀**
