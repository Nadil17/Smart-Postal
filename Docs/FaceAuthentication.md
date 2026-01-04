📦 Secure Parcel Delivery Backend
FastAPI • Face Recognition • ID Verification • IoT Smart Locker System
This backend provides APIs for secure parcel handover using facial recognition and ID card verification, along with IoT locker integration. It ensures parcels are delivered only to the intended recipient—even if redirected to a neighbour or collected from a smart locker.

🚀 System Overview
🔐 Identity & Verification Flow
User uploads a picture of the neighbour’s ID card

Backend extracts & processes the face

Generates and stores encrypted facial embeddings

When the courier arrives:

Courier scans the receiver’s face

Backend verifies the face → returns verified / rejected

For IoT lockers:

User scans face at locker

Backend verifies identity → locker unlocks on success

🧱 Backend Responsibilities
✔ ID Card Processing
Extract face from ID image

Generate embeddings using ML model

Encrypt and store the embedding

✔ Live Face Verification
Compare new live-face embedding with stored ID embedding

Provide similarity score

Return verification response

✔ IoT Locker Integration
Validate face at locker

Generate time-limited unlock tokens

Log locker events (optional)

✔ Security
JWT authentication

Encrypted biometric data only

No raw images stored

HTTPS-only communication

📡 API Endpoints
1. Upload ID Card (Create Identity Profile)
POST /id/upload

Uploads ID card + metadata and stores the face embedding.

Request (multipart/form-data)
image: ID card image

name: User name

phone (optional)

address (optional)

Response
json
Copy code
{
  "message": "ID processed and embedding stored",
  "user_id": "abc12345"
}
2. Face Verification (Courier Delivery)
POST /face/verify

Verifies if a live face matches a stored identity profile.

Request
image: Live face image

user_id: User identity you want to verify against

Response
json
Copy code
{
  "verified": true,
  "confidence": 0.91,
  "threshold": 0.6
}
3. Locker Face Verification
POST /locker/verify

Locker camera sends a face image. System checks and returns unlock permission.

Request
image: Live face image

locker_id: Locker identifier

user_id: Intended parcel owner

Response
json
Copy code
{
  "unlock": true,
  "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
}
4. Locker Unlock Callback (Optional)
POST /locker/unlock

Locker uses the signed token to open the box.

Request
json
Copy code
{
  "token": "jwt token from /locker/verify"
}
Response
json
Copy code
{
  "status": "locker_unlocked"
}
🧠 Face Recognition Logic
Detect face using RetinaFace / MTCNN

Align face

Generate 128d–512d embedding (FaceNet, ArcFace, DeepFace)

Store encrypted embedding

Verification:

Get embedding of live-face input

Compare cosine distance

If < threshold, identity is verified

Default threshold: 0.6 (configurable)

🔒 Security Considerations
Stored:
Encrypted face embeddings

User metadata

Locker logs

Never Stored:
Raw face images

Raw ID card images

Encryption:
AES-256 for embeddings

RSA for token signing

HTTPS enforced for all image uploads

🔌 IoT Locker Communication
Locker → Backend
Send face image for check

Receive unlock response

Backend → Locker
Send signed unlock token

Optional MQTT for real-time events

Locker → Backend (callback)
Confirm unlock event

Log pickup event

📁 Example Integration Workflow
Scenario: Courier delivers parcel to neighbour
Sender uploads neighbour’s ID card → backend saves embedding

Courier arrives at neighbour’s house

Courier app scans neighbour’s face

Sends image → /face/verify

Backend returns verified: true → courier hands parcel

Scenario: User picks up parcel from smart locker
Courier stores parcel in locker

Courier sets user_id for that locker slot

User arrives at locker

Locker scans user face → backend

Backend verifies → sends unlock token

Locker opens if token is valid