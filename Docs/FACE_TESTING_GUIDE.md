# 🧪 Face Recognition Testing Guide

## Quick Start Testing

### 1. **Start Backend Server**

```powershell
cd smart-postal-back-end\backend
python run.py
```

Expected output:
```
INFO: Starting Voice-Fingerprint-Delivery-System v1.0.0
INFO: Environment: development
INFO: Uvicorn running on http://0.0.0.0:8000
```

### 2. **Open Frontend**

Open in browser: `frontend_test/index.html`

### 3. **Login/Register**

Default test account:
- Email: `test@example.com`
- Password: `password123`

---

## Face Recognition Test Scenarios

### **Scenario 1: ID Card Enrollment** ✅

**Steps:**
1. Click "Face ID Enrollment (ID Card)" section
2. Click "Choose File" and select a clear ID card photo
3. Optionally fill in Name, Phone, Address
4. Click "📸 Enroll Face from ID Card"

**Expected Result:**
```
✅ ID card processed and face template stored
👤 User ID: X
🆔 Face ID: Y
📊 Quality Score: 0.85
✅ Liveness Check: PASSED
🔐 Face embedding encrypted and stored
```

**Test Images:**
- Use a clear frontal face photo
- Face should be ≥80x80 pixels
- Good lighting (brightness 0.2-0.9)

---

### **Scenario 2: Face Verification** ✅

**Steps:**
1. Click "Face Verification (Live Photo)" section
2. Enter User ID to verify (use the ID from enrollment)
3. Optionally enter Order ID
4. Upload a live selfie of the enrolled user
5. Click "✅ Verify Face Identity"

**Expected Result (Match):**
```
✅ FACE VERIFIED SUCCESSFULLY!
👤 User ID X identity confirmed
📊 Similarity Score: 75.2%
🎯 Threshold: 60.0%
📈 Confidence: 75.2%
✅ Liveness Check: PASSED
✓ Face verified successfully
```

**Expected Result (No Match):**
```
❌ FACE VERIFICATION FAILED
👤 User ID X not matched
📊 Similarity Score: 35.8%
🎯 Threshold: 60.0%
✗ Face does not match
```

**Test Cases:**
- ✅ Same person, different photo → Should PASS
- ❌ Different person → Should FAIL
- ❌ Photo of photo → Liveness FAIL
- ❌ Screen display of face → Liveness FAIL

---

### **Scenario 3: Smart Locker Unlock** 🔒

**Steps:**
1. Click "Smart Locker Face Unlock" section
2. Enter Locker ID (e.g., `LOCKER-001`)
3. Enter User ID (enrolled user)
4. Optionally enter Parcel ID
5. Upload face photo at "locker camera"
6. Click "🔓 Verify Face at Locker"

**Expected Result (Success):**
```
✅ LOCKER VERIFICATION SUCCESSFUL!
🔓 Unlock token generated
⏱️ Token expires in 300 seconds (5 minutes)
📊 Confidence: 68.5%
```

**Token Display:**
- Green box appears with JWT token
- Copy token or click "🔓 Unlock Locker Now"

**Unlock Locker:**
1. Click "🔓 Unlock Locker Now" button
2. Expected:
   ```
   ✅ Locker unlocked successfully!
   🔓 Locker LOCKER-001 unlocked successfully!
   📋 Status: locker_unlocked
   ```

**Test Cases:**
- ✅ Valid face + valid locker → Generate token
- ❌ Invalid face → No token
- ❌ Expired token (>5min) → Unlock fails
- ❌ Reuse token → Unlock fails (single-use)
- ❌ Wrong locker ID → Unlock fails

---

## API Testing with Postman/curl

### **1. Face Enrollment**

```bash
curl -X POST http://localhost:8000/api/face/id/upload \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -F "file=@path/to/id_card.jpg" \
  -F "name=John Doe" \
  -F "phone=1234567890" \
  -F "address=123 Main St"
```

### **2. Face Verification**

```bash
curl -X POST http://localhost:8000/api/face/verify \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -F "file=@path/to/selfie.jpg" \
  -F "user_id=1" \
  -F "order_id=123"
```

### **3. Locker Verification (No Auth)**

```bash
curl -X POST http://localhost:8000/api/face/locker/verify \
  -F "file=@path/to/face.jpg" \
  -F "locker_id=LOCKER-001" \
  -F "user_id=1" \
  -F "parcel_id=PARCEL-ABC"
```

### **4. Locker Unlock**

```bash
curl -X POST http://localhost:8000/api/face/locker/unlock \
  -H "Content-Type: application/json" \
  -d '{
    "token": "YOUR_JWT_TOKEN",
    "locker_id": "LOCKER-001"
  }'
```

---

## Troubleshooting

### **Issue: "No face detected"**

**Causes:**
- Face too small (<80x80 pixels)
- Face not frontal
- Poor lighting

**Solutions:**
- Use higher resolution image
- Ensure face is facing camera
- Improve lighting conditions
- Try different image

---

### **Issue: "Face processing failed: No module named 'cv2'"**

**Solution:**
```powershell
pip install opencv-python
```

---

### **Issue: "Liveness check failed"**

**Causes:**
- Using a photo of a photo
- Screen display
- Low quality image
- Unusual lighting

**Solutions:**
- Use live camera capture
- Ensure natural lighting
- Move slightly during capture
- Use high-quality camera

---

### **Issue: "Face template corrupted"**

**Causes:**
- Database corruption
- Encryption key changed
- Invalid embedding data

**Solutions:**
1. Delete face template: `DELETE /api/face/template`
2. Re-enroll face
3. Check `.env` encryption key hasn't changed

---

### **Issue: "Token expired" or "Token already used"**

**Explanation:**
- Tokens expire after 5 minutes
- Tokens are single-use for security

**Solutions:**
- Re-verify face to generate new token
- Use token immediately after generation

---

## Expected Performance

### **Processing Times:**
- Face Detection: ~0.5-1 second
- Embedding Extraction: ~1-2 seconds
- Verification: <0.1 second
- **Total**: ~2-4 seconds per operation

### **Accuracy:**
- Detection Rate: 95%+
- False Accept Rate: <1%
- False Reject Rate: ~5%
- Liveness Detection: ~90%

---

## Database Verification

### **Check Face Templates:**

```sql
SELECT 
    id,
    user_id,
    face_quality_score,
    liveness_score,
    anti_spoof_passed,
    enrollment_type,
    created_at
FROM face_templates
WHERE is_active = 1;
```

### **Check Verification Logs:**

```sql
SELECT 
    verification_type,
    success,
    confidence_score,
    ai_detected,
    failure_reason,
    created_at
FROM verification_logs
WHERE verification_type IN ('face', 'face_locker')
ORDER BY created_at DESC
LIMIT 10;
```

---

## Security Testing

### **1. Photo Attack Test** 🚨

**Test:** Upload a photo of a photo
- **Expected:** Liveness check FAIL
- **Reason:** Low texture variance, high edge density

### **2. Screen Attack Test** 🖥️

**Test:** Display face on screen and photograph
- **Expected:** Liveness check FAIL  
- **Reason:** Frequency analysis detects digital display

### **3. Different User Test** 👤

**Test:** Verify with face of different person
- **Expected:** Verification FAIL (similarity <60%)

### **4. Token Replay Test** 🔁

**Test:** Use the same token twice
- **Expected:** Second unlock FAIL (token already used)

### **5. Token Expiry Test** ⏱️

**Test:** Wait 5+ minutes, then unlock
- **Expected:** Unlock FAIL (token expired)

---

## Sample Test Data

### **Good Test Images:**
- ✅ Clear frontal face
- ✅ Natural lighting
- ✅ Face size >80x80 pixels
- ✅ Brightness 0.2-0.9
- ✅ Live camera capture

### **Bad Test Images:**
- ❌ Side profile
- ❌ Too dark/bright
- ❌ Face too small
- ❌ Photo of photo
- ❌ Screen display

---

## Integration Testing

### **Multi-Modal Test (Voice + Face):**

1. **Enroll Voice**: Upload 3 voice samples
2. **Enroll Face**: Upload ID card
3. **Verify Voice**: Test voice authentication
4. **Verify Face**: Test face authentication
5. **Combined**: Use both for highest security

**Use Case:** Courier delivery
- Courier takes recipient's photo
- Recipient speaks passphrase
- Both verifications must pass

---

## Production Checklist

Before deploying to production:

- [ ] Enable HTTPS/TLS for API
- [ ] Set proper CORS origins (not `*`)
- [ ] Add rate limiting on face endpoints
- [ ] Implement device fingerprinting
- [ ] Add geofencing for locker locations
- [ ] Set up monitoring/alerting
- [ ] Configure backup/restore for embeddings
- [ ] Add admin dashboard
- [ ] Implement audit log retention
- [ ] Test with diverse face types
- [ ] Verify GDPR compliance
- [ ] Document privacy policy
- [ ] Train support staff

---

## Next Steps

1. **Test with real images** from your ID card and selfie
2. **Adjust thresholds** if needed (in `utils/face_recognition.py`)
3. **Add camera capture** to frontend for live photos
4. **Implement mobile app** for better camera quality
5. **Deploy to production** server

---

## Support

For issues or questions:
1. Check logs in console/terminal
2. Review `FACE_RECOGNITION_IMPLEMENTATION.md`
3. Inspect database for data integrity
4. Test with different images

**Happy Testing! 🎉**
