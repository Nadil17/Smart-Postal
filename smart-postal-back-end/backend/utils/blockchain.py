"""
================================================================================
BLOCKCHAIN INTEGRATION SERVICE
================================================================================
Connects FastAPI backend to Ethereum/Polygon smart contracts

Features:
- Record delivery proofs on blockchain
- Record COD transactions
- Record neighbor consent
- Query delivery evidence for dispute resolution
- Verify proof integrity
- Cache proofs in database for fast queries

Author: Smart Postal Research Team
================================================================================
"""

from web3 import Web3
from eth_account import Account
import json
import os
from typing import Dict, Any, Optional, List
from datetime import datetime
import asyncio
from pathlib import Path


class BlockchainService:
    """
    Service for interacting with DeliveryProofRegistry smart contract
    
    Supports:
    - Local Hardhat node (development)
    - Ethereum Sepolia testnet
    - Polygon Mumbai testnet
    - Polygon mainnet (production)
    """
    
    # Event type mapping (matches Solidity enum)
    EVENT_TYPES = {
        "CUSTOMER_VERIFIED": 0,
        "NEIGHBOR_VERIFIED": 1,
        "CONSENT_RECORDED": 2,
        "DELIVERY_SUCCESS": 3,
        "DELIVERY_HANDOVER": 4,
        "COD_COLLECTED": 5,
        "LOCKER_DEPOSITED": 6,
        "DISPUTE_RAISED": 7,
        "DISPUTE_RESOLVED": 8
    }
    
    # Verification status mapping
    VERIFICATION_STATUS = {
        "PENDING": 0,
        "PASS": 1,
        "FAIL": 2
    }
    
    def __init__(self):
        # Load configuration
        self.config = self._load_config()
        
        # Initialize Web3
        self.rpc_url = os.getenv("BLOCKCHAIN_RPC_URL", "http://127.0.0.1:8545")
        self.w3 = Web3(Web3.HTTPProvider(self.rpc_url))
        
        # Load contract
        self.contract = self._load_contract()
        
        # Admin account for signing transactions
        self.admin_key = os.getenv("BLOCKCHAIN_ADMIN_KEY", "")
        if self.admin_key:
            try:
                self.admin_account = Account.from_key(self.admin_key)
            except:
                self.admin_account = None
        else:
            self.admin_account = None
        
        self._log_status()
    
    def _load_config(self) -> Dict[str, Any]:
        """Load blockchain configuration"""
        config_paths = [
            Path(__file__).parent.parent / "config" / "blockchain.json",
            Path(__file__).parent.parent.parent.parent / "blockchain" / "deployments" / "localhost-deployment.json",
            Path(__file__).parent.parent.parent.parent / "blockchain" / "deployments" / "hardhat-deployment.json",
        ]
        
        for config_path in config_paths:
            try:
                if config_path.exists():
                    with open(config_path, "r") as f:
                        config = json.load(f)
                        print(f"✅ Loaded blockchain config from: {config_path.name}")
                        return config
            except Exception as e:
                continue
        
        print("⚠️ No blockchain config found. Deploy contracts first.")
        return {}
    
    def _load_contract(self):
        """Load contract ABI and create instance"""
        if not self.config:
            return None
        
        # Possible ABI paths
        abi_paths = [
            Path(__file__).parent.parent.parent.parent / "blockchain" / "artifacts" / "contracts" / "DeliveryProofRegistry.sol" / "DeliveryProofRegistry.json",
        ]
        
        for abi_path in abi_paths:
            try:
                if abi_path.exists():
                    with open(abi_path, "r") as f:
                        contract_json = json.load(f)
                    
                    address = self.config.get("contracts", {}).get("DeliveryProofRegistry")
                    if address:
                        contract = self.w3.eth.contract(
                            address=Web3.to_checksum_address(address),
                            abi=contract_json["abi"]
                        )
                        print(f"✅ Contract loaded: {address[:20]}...")
                        return contract
            except Exception as e:
                print(f"⚠️ Error loading contract ABI: {e}")
                continue
        
        return None
    
    def _log_status(self):
        """Log connection status"""
        print("\n" + "="*50)
        print("⛓️  BLOCKCHAIN SERVICE STATUS")
        print("="*50)
        print(f"   RPC URL: {self.rpc_url}")
        print(f"   Connected: {self.w3.is_connected()}")
        if self.contract:
            print(f"   Contract: {self.contract.address}")
        else:
            print("   Contract: Not loaded (deploy first)")
        if self.admin_account:
            print(f"   Admin: {self.admin_account.address[:20]}...")
        print("="*50 + "\n")
    
    def is_available(self) -> bool:
        """Check if blockchain is available"""
        return self.w3.is_connected() and self.contract is not None
    
    async def _save_proof_to_db(
        self,
        delivery_id: str,
        tx_hash: str,
        block_number: int,
        proof_hash: str,
        verification_type: str,
        verification_status: str,
        confidence_score: float = None,
        ai_model: str = None,
        liveness_passed: bool = True,
        ai_detection_score: float = None,
        recipient_hash: str = None,
        courier_hash: str = None,
        gas_used: int = None,
        gas_price: str = None
    ):
        """
        Save blockchain proof to database for fast queries.
        
        The blockchain remains the source of truth, but this provides
        faster access for dashboard and reporting.
        """
        try:
            from models.database import SessionLocal
            from models.blockchain import BlockchainProof
            
            db = SessionLocal()
            try:
                # Get block timestamp
                block = self.w3.eth.get_block(block_number)
                block_timestamp = datetime.fromtimestamp(block.timestamp)
                
                # Check if already exists
                existing = db.query(BlockchainProof).filter(
                    BlockchainProof.delivery_id == delivery_id
                ).first()
                
                if existing:
                    # Update existing record
                    existing.transaction_hash = tx_hash
                    existing.block_number = block_number
                    existing.block_timestamp = block_timestamp
                    existing.verification_status = verification_status
                    existing.confidence_score = confidence_score
                    existing.gas_used = gas_used
                    print(f"   📊 Database record updated for {delivery_id}")
                else:
                    # Create new record
                    proof_record = BlockchainProof(
                        delivery_id=delivery_id,
                        transaction_hash=tx_hash,
                        block_number=block_number,
                        block_timestamp=block_timestamp,
                        proof_hash=proof_hash,
                        verification_type=verification_type,
                        verification_status=verification_status,
                        confidence_score=confidence_score,
                        ai_model_used=ai_model,
                        liveness_passed=liveness_passed,
                        ai_detection_score=ai_detection_score,
                        recipient_hash=recipient_hash,
                        courier_hash=courier_hash,
                        gas_used=gas_used,
                        gas_price=gas_price
                    )
                    db.add(proof_record)
                    print(f"   📊 Database record created for {delivery_id}")
                
                db.commit()
            finally:
                db.close()
        except Exception as e:
            print(f"   ⚠️ Database save failed (blockchain record still valid): {e}")
    
    def _to_bytes32(self, hex_string: str) -> bytes:
        """Convert hex string to bytes32"""
        if hex_string.startswith("0x"):
            hex_string = hex_string[2:]
        return bytes.fromhex(hex_string.zfill(64))
    
    async def record_proof(
        self,
        token_hash: str,
        commitment_hash: str,
        delivery_id: str,
        event_type: str,
        status: str,
        confidence_score: float,
        gps_latitude: float,
        gps_longitude: float,
        ai_model: str,
        private_key: str
    ) -> Optional[Dict[str, Any]]:
        """
        Record delivery proof on blockchain
        
        This creates an IMMUTABLE record of the verification event.
        Contains NO personal data - only cryptographic proofs.
        
        Returns transaction details on success
        """
        if not self.contract:
            print("⚠️ Contract not available")
            return None
        
        try:
            account = Account.from_key(private_key)
            
            # Convert types
            event_type_int = self.EVENT_TYPES.get(event_type, 0)
            status_int = self.VERIFICATION_STATUS.get(status, 0)
            confidence_int = int(confidence_score * 10000)  # 0.87 -> 8700
            lat_int = int(gps_latitude * 1_000_000)
            lng_int = int(gps_longitude * 1_000_000)
            
            # Build transaction
            tx = self.contract.functions.recordProof(
                self._to_bytes32(token_hash),
                self._to_bytes32(commitment_hash),
                delivery_id,
                event_type_int,
                status_int,
                confidence_int,
                lat_int,
                lng_int,
                ai_model
            ).build_transaction({
                'from': account.address,
                'nonce': self.w3.eth.get_transaction_count(account.address),
                'gas': 500000,
                'gasPrice': self.w3.eth.gas_price
            })
            
            # Sign and send
            signed_tx = self.w3.eth.account.sign_transaction(tx, private_key)
            tx_hash = self.w3.eth.send_raw_transaction(signed_tx.raw_transaction)
            
            # Wait for confirmation
            receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash, timeout=60)
            
            result = {
                "success": True,
                "tx_hash": tx_hash.hex(),
                "block_number": receipt.blockNumber,
                "gas_used": receipt.gasUsed,
                "delivery_id": delivery_id,
                "commitment_hash": commitment_hash,
                "event_type": event_type,
                "timestamp": datetime.utcnow().isoformat()
            }
            
            # Save to database for fast queries
            await self._save_proof_to_db(
                delivery_id=delivery_id,
                tx_hash=tx_hash.hex(),
                block_number=receipt.blockNumber,
                proof_hash=commitment_hash,
                verification_type=event_type.lower().replace("_", " "),
                verification_status=status,
                confidence_score=confidence_score,
                ai_model=ai_model,
                gas_used=receipt.gasUsed
            )
            
            print(f"\n✅ Proof recorded on blockchain")
            print(f"   TX: {tx_hash.hex()[:20]}...")
            print(f"   Block: {receipt.blockNumber}")
            print(f"   Gas: {receipt.gasUsed}")
            
            return result
            
        except Exception as e:
            print(f"❌ Blockchain error: {e}")
            return {"success": False, "error": str(e)}
    
    async def record_cod(
        self,
        delivery_id: str,
        cod_commitment_hash: str,
        customer_commitment_hash: str,
        amount_lkr: int,
        spoken_confirmation_hash: str,
        gps_latitude: float,
        gps_longitude: float,
        private_key: str
    ) -> Optional[Dict[str, Any]]:
        """
        Record COD (Cash on Delivery) collection on blockchain
        
        Creates immutable proof of:
        - WHO received the payment (commitment hash)
        - HOW MUCH was paid
        - WHERE payment was collected
        - WHEN payment was collected
        """
        if not self.contract:
            return None
        
        try:
            account = Account.from_key(private_key)
            
            lat_int = int(gps_latitude * 1_000_000)
            lng_int = int(gps_longitude * 1_000_000)
            
            tx = self.contract.functions.recordCOD(
                delivery_id,
                self._to_bytes32(cod_commitment_hash),
                self._to_bytes32(customer_commitment_hash),
                amount_lkr,
                self._to_bytes32(spoken_confirmation_hash),
                lat_int,
                lng_int
            ).build_transaction({
                'from': account.address,
                'nonce': self.w3.eth.get_transaction_count(account.address),
                'gas': 300000,
                'gasPrice': self.w3.eth.gas_price
            })
            
            signed_tx = self.w3.eth.account.sign_transaction(tx, private_key)
            tx_hash = self.w3.eth.send_raw_transaction(signed_tx.raw_transaction)
            receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash, timeout=60)
            
            print(f"\n✅ COD recorded on blockchain")
            print(f"   Amount: LKR {amount_lkr:,}")
            print(f"   TX: {tx_hash.hex()[:20]}...")
            
            # Save to database
            await self._save_proof_to_db(
                delivery_id=delivery_id,
                tx_hash=tx_hash.hex(),
                block_number=receipt.blockNumber,
                proof_hash=cod_commitment_hash,
                verification_type="cod_collected",
                verification_status="PASS",
                gas_used=receipt.gasUsed
            )
            
            return {
                "success": True,
                "tx_hash": tx_hash.hex(),
                "block_number": receipt.blockNumber,
                "amount_lkr": amount_lkr,
                "delivery_id": delivery_id
            }
            
        except Exception as e:
            print(f"❌ COD recording error: {e}")
            return {"success": False, "error": str(e)}
    
    async def record_consent(
        self,
        delivery_id: str,
        consent_hash: str,
        neighbor_commitment_hash: str,
        consent_given: bool,
        customer_gps_latitude: float,
        customer_gps_longitude: float
    ) -> Optional[Dict[str, Any]]:
        """
        Record neighbor consent on blockchain
        
        Creates immutable proof of customer's consent for third-party delivery.
        """
        if not self.contract or not self.admin_account:
            return None
        
        try:
            lat_int = int(customer_gps_latitude * 1_000_000)
            lng_int = int(customer_gps_longitude * 1_000_000)
            
            tx = self.contract.functions.recordConsent(
                delivery_id,
                self._to_bytes32(consent_hash),
                self._to_bytes32(neighbor_commitment_hash),
                consent_given,
                lat_int,
                lng_int
            ).build_transaction({
                'from': self.admin_account.address,
                'nonce': self.w3.eth.get_transaction_count(self.admin_account.address),
                'gas': 200000,
                'gasPrice': self.w3.eth.gas_price
            })
            
            signed_tx = self.w3.eth.account.sign_transaction(tx, self.admin_key)
            tx_hash = self.w3.eth.send_raw_transaction(signed_tx.raw_transaction)
            receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash, timeout=60)
            
            print(f"\n✅ Consent recorded on blockchain")
            print(f"   Consent: {'YES' if consent_given else 'NO'}")
            print(f"   TX: {tx_hash.hex()[:20]}...")
            
            # Save to database
            await self._save_proof_to_db(
                delivery_id=delivery_id,
                tx_hash=tx_hash.hex(),
                block_number=receipt.blockNumber,
                proof_hash=consent_hash,
                verification_type="neighbor_consent",
                verification_status="PASS" if consent_given else "FAIL",
                gas_used=receipt.gasUsed
            )
            
            return {
                "success": True,
                "tx_hash": tx_hash.hex(),
                "block_number": receipt.blockNumber,
                "consent_given": consent_given
            }
            
        except Exception as e:
            print(f"❌ Consent recording error: {e}")
            return {"success": False, "error": str(e)}
    
    def get_delivery_evidence(self, delivery_id: str) -> Optional[Dict[str, Any]]:
        """
        Get all blockchain evidence for a delivery
        
        Used for dispute resolution. Provides complete audit trail
        WITHOUT exposing personal data.
        
        LEGAL: Admissible under Electronic Transactions Act, Section 21
        """
        if not self.contract:
            return None
        
        try:
            evidence = self.contract.functions.getDeliveryEvidence(delivery_id).call()
            
            return {
                "delivery_id": delivery_id,
                "proof_count": evidence[0],
                "has_cod": evidence[1],
                "cod_amount_lkr": evidence[2],
                "has_consent": evidence[3],
                "consent_given": evidence[4],
                "dispute_count": evidence[5],
                "first_proof_timestamp": evidence[6],
                "last_proof_timestamp": evidence[7],
                "blockchain_verified": True,
                "immutable": True,
                "legal_admissibility": "ETA Section 21 compliant"
            }
        except Exception as e:
            print(f"❌ Error getting evidence: {e}")
            return None
    
    def get_proof_details(self, proof_id: int) -> Optional[Dict[str, Any]]:
        """Get detailed proof information"""
        if not self.contract:
            return None
        
        try:
            proof = self.contract.functions.getProof(proof_id).call()
            
            event_types = ["CUSTOMER_VERIFIED", "NEIGHBOR_VERIFIED", "CONSENT_RECORDED",
                          "DELIVERY_SUCCESS", "DELIVERY_HANDOVER", "COD_COLLECTED",
                          "LOCKER_DEPOSITED", "DISPUTE_RAISED", "DISPUTE_RESOLVED"]
            statuses = ["PENDING", "PASS", "FAIL"]
            
            return {
                "proof_id": proof_id,
                "token_hash": "0x" + proof[0].hex(),
                "commitment_hash": "0x" + proof[1].hex(),
                "delivery_id": proof[2],
                "event_type": event_types[proof[3]] if proof[3] < len(event_types) else "UNKNOWN",
                "status": statuses[proof[4]] if proof[4] < len(statuses) else "UNKNOWN",
                "confidence_score": proof[5] / 100,  # Convert to percentage
                "timestamp": proof[6],
                "gps_latitude": proof[7] / 1_000_000,
                "gps_longitude": proof[8] / 1_000_000,
                "courier": proof[9],
                "ai_model": proof[10]
            }
        except Exception as e:
            print(f"❌ Error getting proof: {e}")
            return None
    
    def get_statistics(self) -> Optional[Dict[str, Any]]:
        """Get blockchain statistics"""
        if not self.contract:
            return None
        
        try:
            stats = self.contract.functions.getStatistics().call()
            
            return {
                "total_deliveries": stats[0],
                "total_verifications": stats[1],
                "total_cod_transactions": stats[2],
                "total_cod_amount_lkr": stats[3],
                "total_disputes": stats[4],
                "resolved_disputes": stats[5],
                "dispute_resolution_rate": f"{stats[6] / 100:.2f}%",
                "blockchain_active": True
            }
        except Exception as e:
            print(f"❌ Error getting statistics: {e}")
            return None
    
    async def register_courier(self, courier_address: str) -> Optional[Dict[str, Any]]:
        """Register a new courier on blockchain"""
        if not self.contract or not self.admin_account:
            return None
        
        try:
            tx = self.contract.functions.registerCourier(
                Web3.to_checksum_address(courier_address)
            ).build_transaction({
                'from': self.admin_account.address,
                'nonce': self.w3.eth.get_transaction_count(self.admin_account.address),
                'gas': 100000,
                'gasPrice': self.w3.eth.gas_price
            })
            
            signed_tx = self.w3.eth.account.sign_transaction(tx, self.admin_key)
            tx_hash = self.w3.eth.send_raw_transaction(signed_tx.raw_transaction)
            receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash, timeout=60)
            
            return {
                "success": True,
                "courier_address": courier_address,
                "tx_hash": tx_hash.hex()
            }
        except Exception as e:
            return {"success": False, "error": str(e)}


# ============================================================================
# GLOBAL INSTANCE
# ============================================================================

# Initialize blockchain service (will connect on first use)
try:
    blockchain_service = BlockchainService()
except Exception as e:
    print(f"⚠️ Blockchain service initialization deferred: {e}")
    blockchain_service = None


def get_blockchain_service() -> Optional[BlockchainService]:
    """Get blockchain service instance"""
    global blockchain_service
    if blockchain_service is None:
        try:
            blockchain_service = BlockchainService()
        except Exception as e:
            print(f"⚠️ Could not initialize blockchain service: {e}")
    return blockchain_service
