"""
Quick test script to verify blockchain integration
"""
import sys
import os
import asyncio

# Add the backend directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Set environment variable for local development
os.environ["BLOCKCHAIN_ADMIN_KEY"] = "0xac0974bec39a17e36ba4a6b4d238ff944bacb478cbed5efcae784d7bf4f2ff80"
PRIVATE_KEY = "0xac0974bec39a17e36ba4a6b4d238ff944bacb478cbed5efcae784d7bf4f2ff80"

from utils.crypto_commitment import CryptographicCommitmentEngine, EventType
from utils.blockchain import BlockchainService

def test_crypto_commitment():
    """Test the cryptographic commitment engine"""
    print("\n" + "="*60)
    print("🔐 TESTING CRYPTOGRAPHIC COMMITMENT ENGINE")
    print("="*60)
    
    engine = CryptographicCommitmentEngine()
    
    # Test 1: Create identity commitment
    print("\n📋 Test 1: Identity Commitment")
    nic = "200012345678"  # Sample Sri Lankan NIC
    face_embedding = [0.1] * 512  # Simulated face embedding
    
    commitment = engine.create_identity_commitment(
        nic_number=nic,
        face_embedding=face_embedding,
        liveness_result=True,
        ai_confidence=0.95,
        delivery_id="TEST-DELIVERY-001",
        event_type=EventType.CUSTOMER_VERIFIED,
        gps_latitude=6.9271,
        gps_longitude=79.8612,
        ai_model="ArcFace"
    )
    
    print(f"   NIC: {nic}")
    print(f"   Commitment Hash: {commitment.commitment_hash[:40]}...")
    print(f"   Shamir Shares: {len(commitment.salt_shares)} shares")
    print(f"   Verification Status: {commitment.verification_status}")
    print(f"   Confidence: {commitment.confidence_score}")
    
    # Test 2: Create proof token
    print("\n📋 Test 2: Proof Token Generation")
    proof = engine.create_proof_token(commitment)
    print(f"   Token Hash: {proof.token_hash[:40]}...")
    print(f"   Delivery ID: {proof.delivery_id}")
    print(f"   Timestamp: {proof.timestamp}")
    
    return commitment, proof

async def test_blockchain_service():
    """Test blockchain service"""
    print("\n" + "="*60)
    print("⛓️  TESTING BLOCKCHAIN SERVICE")
    print("="*60)
    
    service = BlockchainService()
    
    if not service.w3.is_connected():
        print("❌ Not connected to blockchain")
        print("   Make sure Hardhat node is running: npx hardhat node")
        return
    
    if not service.contract:
        print("❌ Contract not loaded")
        print("   Make sure contract is deployed")
        return
    
    print(f"\n✅ Connected to blockchain at {service.rpc_url}")
    print(f"✅ Contract loaded at {service.contract.address}")
    
    # Test: Record a proof
    print("\n📋 Test: Record Delivery Proof")
    
    engine = CryptographicCommitmentEngine()
    commitment = engine.create_identity_commitment(
        nic_number="200012345678",
        face_embedding=[0.1] * 512,
        liveness_result=True,
        ai_confidence=0.95,
        delivery_id="TEST-DELIVERY-002",
        event_type=EventType.CUSTOMER_VERIFIED,
        gps_latitude=6.9271,
        gps_longitude=79.8612
    )
    
    # Create proof token
    proof = engine.create_proof_token(commitment)
    
    result = await service.record_proof(
        token_hash=proof.token_hash,
        commitment_hash=commitment.commitment_hash,
        delivery_id="TEST-DELIVERY-002",
        event_type="CUSTOMER_VERIFIED",
        status="PASS",
        confidence_score=0.95,
        gps_latitude=6.9271,
        gps_longitude=79.8612,
        ai_model="ArcFace",
        private_key=PRIVATE_KEY
    )
    
    if result and result.get("success"):
        print(f"   ✅ Proof recorded on blockchain!")
        print(f"   TX Hash: {result['tx_hash'][:40]}...")
        print(f"   Block: {result['block_number']}")
        print(f"   Gas Used: {result['gas_used']}")
    else:
        print(f"   ❌ Error: {result.get('error') if result else 'No result'}")
    
    # Test: Get delivery evidence
    print("\n📋 Test: Retrieve Delivery Evidence")
    evidence = service.get_delivery_evidence("TEST-DELIVERY-002")
    
    if evidence:
        print(f"   ✅ Evidence retrieved!")
        print(f"   Proof Count: {evidence.get('proof_count', 0)}")
        if evidence.get('proofs'):
            for i, p in enumerate(evidence['proofs'][:3]):
                print(f"   Proof {i+1}: {p.get('event_type', 'N/A')}")
    else:
        print(f"   ⚠️ No evidence found")
    
    # Test: Get statistics
    print("\n📋 Test: Get Protocol Statistics")
    stats = service.get_statistics()
    print(f"   Total Deliveries: {stats.get('total_deliveries', 0)}")
    print(f"   Total Proofs: {stats.get('total_proofs', 0)}")
    print(f"   Successful Verifications: {stats.get('successful_verifications', 0)}")

if __name__ == "__main__":
    print("\n" + "="*70)
    print("   SMART POSTAL - BLOCKCHAIN INTEGRATION TEST")
    print("   Privacy-First Delivery Verification Protocol")
    print("="*70)
    
    try:
        commitment, proof = test_crypto_commitment()
        asyncio.run(test_blockchain_service())
        
        print("\n" + "="*70)
        print("   ✅ ALL TESTS COMPLETED")
        print("="*70 + "\n")
    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
