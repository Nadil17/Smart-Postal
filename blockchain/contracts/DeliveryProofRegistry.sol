// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import "@openzeppelin/contracts/access/AccessControl.sol";
import "@openzeppelin/contracts/utils/ReentrancyGuard.sol";

/**
 * @title DeliveryProofRegistry
 * @author Smart Postal Research Team
 * @notice Privacy-First Delivery Verification Protocol
 * 
 * @dev Research Implementation:
 * ========================================================================
 * This contract implements the cryptographic commitment protocol described
 * in the research proposal "Privacy-First, Blockchain-Backed Identity-
 * Verified Last-Mile Delivery".
 * 
 * KEY PRIVACY PROPERTIES:
 * - NO personal data stored on-chain (only cryptographic hashes)
 * - Commitments cannot be reversed to reveal identity
 * - PDPA-compliant by design (Sri Lanka's Personal Data Protection Act)
 * - Admissible under Electronic Transactions Act, No. 19 of 2006 (Section 21)
 * 
 * PROTOCOL:
 * 1. Identity data processed LOCALLY on courier device
 * 2. COMMITMENT = SHA-3-256(NIC || SALT || BIOMETRIC_HASH)
 * 3. Salt split using Shamir Secret Sharing (no single entity can reverse)
 * 4. Only commitment hash stored on blockchain
 * 5. Raw data deleted immediately after commitment creation
 * ========================================================================
 */
contract DeliveryProofRegistry is AccessControl, ReentrancyGuard {
    
    // ============== ROLES ==============
    bytes32 public constant COURIER_ROLE = keccak256("COURIER_ROLE");
    bytes32 public constant ADMIN_ROLE = keccak256("ADMIN_ROLE");
    bytes32 public constant AUDITOR_ROLE = keccak256("AUDITOR_ROLE");
    
    // ============== COUNTERS ==============
    uint256 private _proofIdCounter;
    uint256 private _disputeIdCounter;
    
    // ============== ENUMS ==============
    
    /**
     * @notice Types of delivery events recorded on-chain
     */
    enum EventType {
        CUSTOMER_VERIFIED,      // Customer identity verified at delivery
        NEIGHBOR_VERIFIED,      // Neighbor identity verified for third-party delivery
        CONSENT_RECORDED,       // Customer consent for neighbor delivery
        DELIVERY_SUCCESS,       // Delivery completed successfully
        DELIVERY_HANDOVER,      // Parcel handed to third party
        COD_COLLECTED,          // Cash on Delivery collected
        LOCKER_DEPOSITED,       // Parcel deposited in smart locker
        DISPUTE_RAISED,         // Dispute raised by customer/courier
        DISPUTE_RESOLVED        // Dispute resolved by admin
    }
    
    /**
     * @notice Verification status from AI system
     */
    enum VerificationStatus {
        PENDING,    // Verification not yet completed
        PASS,       // Identity verified successfully
        FAIL        // Identity verification failed
    }
    
    /**
     * @notice Dispute resolution status
     */
    enum DisputeStatus {
        OPEN,                       // Dispute open for review
        UNDER_REVIEW,               // Being reviewed by admin
        RESOLVED_CUSTOMER_FAVOR,    // Resolved in customer's favor
        RESOLVED_COURIER_FAVOR,     // Resolved in courier's favor
        RESOLVED_SETTLED            // Settled by mutual agreement
    }
    
    // ============== STRUCTS ==============
    
    /**
     * @notice Delivery proof record (NO PERSONAL DATA)
     * @dev Contains only cryptographic hashes and metadata
     * 
     * Privacy Guarantee:
     * - tokenHash: Hash of entire proof token (for integrity verification)
     * - commitmentHash: SHA-3-256(NIC || SALT || BIOMETRIC_HASH) - not reversible
     * - No raw NIC, no biometric data, no personal information
     */
    struct DeliveryProof {
        uint256 proofId;
        bytes32 tokenHash;           // Hash of entire proof token
        bytes32 commitmentHash;      // Cryptographic commitment (not reversible)
        string deliveryId;           // External delivery ID
        EventType eventType;
        VerificationStatus status;
        uint256 confidenceScore;     // AI confidence: 0-10000 (0.00% - 100.00%)
        uint256 timestamp;
        int256 gpsLatitude;          // Multiplied by 1e6 for precision
        int256 gpsLongitude;         // Multiplied by 1e6 for precision
        address courier;
        string aiModel;              // AI model used (e.g., "ArcFace")
    }
    
    /**
     * @notice COD (Cash on Delivery) proof
     * @dev Links payment to identity verification without exposing identity
     */
    struct CODProof {
        bytes32 codCommitmentHash;       // Hash(customerCommitment || amount || timestamp)
        bytes32 customerCommitmentHash;  // Customer's identity commitment
        uint256 amountLKR;               // Amount in LKR
        bytes32 spokenConfirmationHash;  // Hash of voice confirmation
        uint256 timestamp;
        int256 gpsLatitude;
        int256 gpsLongitude;
        string deliveryId;
    }
    
    /**
     * @notice Third-party consent record
     * @dev Records customer's explicit consent for neighbor to receive parcel
     */
    struct ConsentRecord {
        bytes32 consentHash;              // Hash of consent data
        bytes32 neighborCommitmentHash;   // Neighbor's identity commitment
        bool consentGiven;                // true = YES, false = NO
        uint256 timestamp;
        int256 customerGpsLatitude;       // Customer's GPS when consent given
        int256 customerGpsLongitude;
        string deliveryId;
    }
    
    /**
     * @notice Dispute record for resolution
     */
    struct Dispute {
        uint256 disputeId;
        string deliveryId;
        address disputedBy;
        string reason;
        DisputeStatus status;
        uint256 createdAt;
        uint256 resolvedAt;
        string resolution;
    }
    
    // ============== STATE VARIABLES ==============
    
    // Delivery ID => Array of proof IDs (multiple events per delivery)
    mapping(string => uint256[]) public deliveryProofs;
    
    // Proof ID => DeliveryProof
    mapping(uint256 => DeliveryProof) public proofs;
    
    // Delivery ID => CODProof
    mapping(string => CODProof) public codProofs;
    
    // Delivery ID => ConsentRecord
    mapping(string => ConsentRecord) public consentRecords;
    
    // Dispute ID => Dispute
    mapping(uint256 => Dispute) public disputes;
    
    // Delivery ID => Dispute IDs
    mapping(string => uint256[]) public deliveryDisputes;
    
    // Commitment hash => bool (prevent replay attacks)
    mapping(bytes32 => bool) public usedCommitments;
    
    // Statistics
    uint256 public totalDeliveries;
    uint256 public totalVerifications;
    uint256 public totalCODTransactions;
    uint256 public totalCODAmountLKR;
    uint256 public totalDisputes;
    uint256 public resolvedDisputes;
    
    // ============== EVENTS ==============
    
    event ProofRecorded(
        uint256 indexed proofId,
        string indexed deliveryId,
        EventType eventType,
        bytes32 commitmentHash,
        VerificationStatus status,
        uint256 confidenceScore,
        uint256 timestamp
    );
    
    event CODRecorded(
        string indexed deliveryId,
        uint256 amountLKR,
        bytes32 codCommitmentHash,
        uint256 timestamp
    );
    
    event ConsentRecorded(
        string indexed deliveryId,
        bool consentGiven,
        bytes32 neighborCommitmentHash,
        uint256 timestamp
    );
    
    event DisputeRaised(
        uint256 indexed disputeId,
        string indexed deliveryId,
        address indexed disputedBy,
        string reason,
        uint256 timestamp
    );
    
    event DisputeResolved(
        uint256 indexed disputeId,
        string indexed deliveryId,
        DisputeStatus status,
        string resolution,
        uint256 timestamp
    );
    
    event CourierRegistered(address indexed courier, uint256 timestamp);
    event CourierRemoved(address indexed courier, uint256 timestamp);
    
    // ============== CONSTRUCTOR ==============
    
    constructor() {
        _grantRole(DEFAULT_ADMIN_ROLE, msg.sender);
        _grantRole(ADMIN_ROLE, msg.sender);
    }
    
    // ============== MAIN FUNCTIONS ==============
    
    /**
     * @notice Record a delivery verification proof
     * @dev Called by courier app after identity verification
     * 
     * PRIVACY: This function receives only cryptographic hashes.
     * The actual identity verification happens LOCALLY on the courier device.
     * Raw NIC and biometric data are NEVER transmitted to the blockchain.
     * 
     * @param _tokenHash Hash of the entire proof token
     * @param _commitmentHash Cryptographic commitment SHA-3-256(NIC || SALT || BIOMETRIC_HASH)
     * @param _deliveryId External delivery identifier
     * @param _eventType Type of delivery event
     * @param _status Verification status from AI
     * @param _confidenceScore AI confidence score (0-10000)
     * @param _gpsLatitude GPS latitude * 1e6
     * @param _gpsLongitude GPS longitude * 1e6
     * @param _aiModel AI model used for verification
     */
    function recordProof(
        bytes32 _tokenHash,
        bytes32 _commitmentHash,
        string calldata _deliveryId,
        EventType _eventType,
        VerificationStatus _status,
        uint256 _confidenceScore,
        int256 _gpsLatitude,
        int256 _gpsLongitude,
        string calldata _aiModel
    ) external onlyRole(COURIER_ROLE) nonReentrant {
        // Security: Prevent replay attacks
        require(!usedCommitments[_commitmentHash], "Commitment already used");
        require(_confidenceScore <= 10000, "Invalid confidence score");
        require(bytes(_deliveryId).length > 0, "Empty delivery ID");
        
        usedCommitments[_commitmentHash] = true;
        _proofIdCounter++;
        uint256 proofId = _proofIdCounter;
        
        proofs[proofId] = DeliveryProof({
            proofId: proofId,
            tokenHash: _tokenHash,
            commitmentHash: _commitmentHash,
            deliveryId: _deliveryId,
            eventType: _eventType,
            status: _status,
            confidenceScore: _confidenceScore,
            timestamp: block.timestamp,
            gpsLatitude: _gpsLatitude,
            gpsLongitude: _gpsLongitude,
            courier: msg.sender,
            aiModel: _aiModel
        });
        
        deliveryProofs[_deliveryId].push(proofId);
        totalVerifications++;
        
        // Track unique deliveries
        if (deliveryProofs[_deliveryId].length == 1) {
            totalDeliveries++;
        }
        
        emit ProofRecorded(
            proofId,
            _deliveryId,
            _eventType,
            _commitmentHash,
            _status,
            _confidenceScore,
            block.timestamp
        );
    }
    
    /**
     * @notice Record COD (Cash on Delivery) collection proof
     * @dev Links payment amount to identity verification
     * 
     * PRIVACY: Amount is stored (required for dispute resolution),
     * but identity is protected by commitment hash.
     * 
     * @param _deliveryId Delivery identifier
     * @param _codCommitmentHash Hash(customerCommitment || amount || timestamp)
     * @param _customerCommitmentHash Customer's identity commitment
     * @param _amountLKR Amount collected in LKR
     * @param _spokenConfirmationHash Hash of spoken confirmation
     * @param _gpsLatitude GPS latitude * 1e6
     * @param _gpsLongitude GPS longitude * 1e6
     */
    function recordCOD(
        string calldata _deliveryId,
        bytes32 _codCommitmentHash,
        bytes32 _customerCommitmentHash,
        uint256 _amountLKR,
        bytes32 _spokenConfirmationHash,
        int256 _gpsLatitude,
        int256 _gpsLongitude
    ) external onlyRole(COURIER_ROLE) nonReentrant {
        require(codProofs[_deliveryId].timestamp == 0, "COD already recorded");
        require(_amountLKR > 0, "Invalid COD amount");
        
        codProofs[_deliveryId] = CODProof({
            codCommitmentHash: _codCommitmentHash,
            customerCommitmentHash: _customerCommitmentHash,
            amountLKR: _amountLKR,
            spokenConfirmationHash: _spokenConfirmationHash,
            timestamp: block.timestamp,
            gpsLatitude: _gpsLatitude,
            gpsLongitude: _gpsLongitude,
            deliveryId: _deliveryId
        });
        
        totalCODTransactions++;
        totalCODAmountLKR += _amountLKR;
        
        emit CODRecorded(_deliveryId, _amountLKR, _codCommitmentHash, block.timestamp);
    }
    
    /**
     * @notice Record customer consent for third-party delivery
     * @dev Records customer's explicit consent for neighbor to receive parcel
     * 
     * LEGAL: This creates an immutable record of consent, admissible under
     * Sri Lanka's Electronic Transactions Act (Section 21).
     * 
     * @param _deliveryId Delivery identifier
     * @param _consentHash Hash of consent data
     * @param _neighborCommitmentHash Neighbor's identity commitment
     * @param _consentGiven Whether customer gave consent
     * @param _customerGpsLatitude Customer's GPS latitude * 1e6
     * @param _customerGpsLongitude Customer's GPS longitude * 1e6
     */
    function recordConsent(
        string calldata _deliveryId,
        bytes32 _consentHash,
        bytes32 _neighborCommitmentHash,
        bool _consentGiven,
        int256 _customerGpsLatitude,
        int256 _customerGpsLongitude
    ) external onlyRole(ADMIN_ROLE) {
        require(consentRecords[_deliveryId].timestamp == 0, "Consent already recorded");
        
        consentRecords[_deliveryId] = ConsentRecord({
            consentHash: _consentHash,
            neighborCommitmentHash: _neighborCommitmentHash,
            consentGiven: _consentGiven,
            timestamp: block.timestamp,
            customerGpsLatitude: _customerGpsLatitude,
            customerGpsLongitude: _customerGpsLongitude,
            deliveryId: _deliveryId
        });
        
        emit ConsentRecorded(
            _deliveryId,
            _consentGiven,
            _neighborCommitmentHash,
            block.timestamp
        );
    }
    
    /**
     * @notice Raise a dispute for a delivery
     * @dev Creates an immutable dispute record
     * 
     * @param _deliveryId Delivery identifier
     * @param _reason Reason for dispute
     */
    function raiseDispute(
        string calldata _deliveryId,
        string calldata _reason
    ) external {
        require(deliveryProofs[_deliveryId].length > 0, "Delivery not found");
        require(bytes(_reason).length > 0, "Reason required");
        
        _disputeIdCounter++;
        uint256 disputeId = _disputeIdCounter;
        
        disputes[disputeId] = Dispute({
            disputeId: disputeId,
            deliveryId: _deliveryId,
            disputedBy: msg.sender,
            reason: _reason,
            status: DisputeStatus.OPEN,
            createdAt: block.timestamp,
            resolvedAt: 0,
            resolution: ""
        });
        
        deliveryDisputes[_deliveryId].push(disputeId);
        totalDisputes++;
        
        emit DisputeRaised(disputeId, _deliveryId, msg.sender, _reason, block.timestamp);
    }
    
    /**
     * @notice Resolve a dispute
     * @dev Admin-only function to resolve disputes
     * 
     * @param _disputeId Dispute identifier
     * @param _status Resolution status
     * @param _resolution Resolution description
     */
    function resolveDispute(
        uint256 _disputeId,
        DisputeStatus _status,
        string calldata _resolution
    ) external onlyRole(ADMIN_ROLE) {
        require(disputes[_disputeId].createdAt > 0, "Dispute not found");
        require(
            _status == DisputeStatus.RESOLVED_CUSTOMER_FAVOR ||
            _status == DisputeStatus.RESOLVED_COURIER_FAVOR ||
            _status == DisputeStatus.RESOLVED_SETTLED,
            "Invalid resolution status"
        );
        
        Dispute storage dispute = disputes[_disputeId];
        dispute.status = _status;
        dispute.resolution = _resolution;
        dispute.resolvedAt = block.timestamp;
        resolvedDisputes++;
        
        emit DisputeResolved(
            _disputeId,
            dispute.deliveryId,
            _status,
            _resolution,
            block.timestamp
        );
    }
    
    // ============== VIEW FUNCTIONS ==============
    
    /**
     * @notice Get all proof IDs for a delivery
     * @param _deliveryId Delivery identifier
     * @return Array of proof IDs
     */
    function getDeliveryProofIds(string calldata _deliveryId) 
        external view returns (uint256[] memory) 
    {
        return deliveryProofs[_deliveryId];
    }
    
    /**
     * @notice Get proof details
     * @param _proofId Proof identifier
     */
    function getProof(uint256 _proofId) external view returns (
        bytes32 tokenHash,
        bytes32 commitmentHash,
        string memory deliveryId,
        EventType eventType,
        VerificationStatus status,
        uint256 confidenceScore,
        uint256 timestamp,
        int256 gpsLatitude,
        int256 gpsLongitude,
        address courier,
        string memory aiModel
    ) {
        DeliveryProof storage p = proofs[_proofId];
        return (
            p.tokenHash,
            p.commitmentHash,
            p.deliveryId,
            p.eventType,
            p.status,
            p.confidenceScore,
            p.timestamp,
            p.gpsLatitude,
            p.gpsLongitude,
            p.courier,
            p.aiModel
        );
    }
    
    /**
     * @notice Get COD proof for a delivery
     * @param _deliveryId Delivery identifier
     */
    function getCODProof(string calldata _deliveryId) external view returns (
        bytes32 codCommitmentHash,
        bytes32 customerCommitmentHash,
        uint256 amountLKR,
        bytes32 spokenConfirmationHash,
        uint256 timestamp,
        int256 gpsLatitude,
        int256 gpsLongitude
    ) {
        CODProof storage c = codProofs[_deliveryId];
        return (
            c.codCommitmentHash,
            c.customerCommitmentHash,
            c.amountLKR,
            c.spokenConfirmationHash,
            c.timestamp,
            c.gpsLatitude,
            c.gpsLongitude
        );
    }
    
    /**
     * @notice Get consent record for a delivery
     * @param _deliveryId Delivery identifier
     */
    function getConsentRecord(string calldata _deliveryId) external view returns (
        bytes32 consentHash,
        bytes32 neighborCommitmentHash,
        bool consentGiven,
        uint256 timestamp,
        int256 customerGpsLatitude,
        int256 customerGpsLongitude
    ) {
        ConsentRecord storage c = consentRecords[_deliveryId];
        return (
            c.consentHash,
            c.neighborCommitmentHash,
            c.consentGiven,
            c.timestamp,
            c.customerGpsLatitude,
            c.customerGpsLongitude
        );
    }
    
    /**
     * @notice Get complete delivery evidence for dispute resolution
     * @dev Used by courts/auditors to verify delivery proof
     * 
     * LEGAL ADMISSIBILITY: This function provides all evidence
     * WITHOUT exposing personal data, compliant with:
     * - Electronic Transactions Act, No. 19 of 2006 (Section 21)
     * - Personal Data Protection Act, No. 9 of 2022 (Section 7 - Data Minimization)
     * 
     * @param _deliveryId Delivery identifier
     */
    function getDeliveryEvidence(string calldata _deliveryId) external view returns (
        uint256 proofCount,
        bool hasCOD,
        uint256 codAmountLKR,
        bool hasConsent,
        bool consentGiven,
        uint256 disputeCount,
        uint256 firstProofTimestamp,
        uint256 lastProofTimestamp
    ) {
        uint256[] storage proofIds = deliveryProofs[_deliveryId];
        uint256 firstTs = 0;
        uint256 lastTs = 0;
        
        if (proofIds.length > 0) {
            firstTs = proofs[proofIds[0]].timestamp;
            lastTs = proofs[proofIds[proofIds.length - 1]].timestamp;
        }
        
        return (
            proofIds.length,
            codProofs[_deliveryId].timestamp > 0,
            codProofs[_deliveryId].amountLKR,
            consentRecords[_deliveryId].timestamp > 0,
            consentRecords[_deliveryId].consentGiven,
            deliveryDisputes[_deliveryId].length,
            firstTs,
            lastTs
        );
    }
    
    /**
     * @notice Verify proof integrity (for courts/auditors)
     * @param _proofId Proof identifier
     * @param _expectedTokenHash Expected token hash
     * @return True if proof is valid and unchanged
     */
    function verifyProofIntegrity(
        uint256 _proofId,
        bytes32 _expectedTokenHash
    ) external view returns (bool) {
        return proofs[_proofId].tokenHash == _expectedTokenHash;
    }
    
    /**
     * @notice Get dispute details
     * @param _disputeId Dispute identifier
     */
    function getDispute(uint256 _disputeId) external view returns (
        string memory deliveryId,
        address disputedBy,
        string memory reason,
        DisputeStatus status,
        uint256 createdAt,
        uint256 resolvedAt,
        string memory resolution
    ) {
        Dispute storage d = disputes[_disputeId];
        return (
            d.deliveryId,
            d.disputedBy,
            d.reason,
            d.status,
            d.createdAt,
            d.resolvedAt,
            d.resolution
        );
    }
    
    /**
     * @notice Get system statistics
     */
    function getStatistics() external view returns (
        uint256 _totalDeliveries,
        uint256 _totalVerifications,
        uint256 _totalCODTransactions,
        uint256 _totalCODAmountLKR,
        uint256 _totalDisputes,
        uint256 _resolvedDisputes,
        uint256 _disputeResolutionRate
    ) {
        uint256 resolutionRate = totalDisputes > 0 
            ? (resolvedDisputes * 10000) / totalDisputes 
            : 0;
            
        return (
            totalDeliveries,
            totalVerifications,
            totalCODTransactions,
            totalCODAmountLKR,
            totalDisputes,
            resolvedDisputes,
            resolutionRate
        );
    }
    
    // ============== ADMIN FUNCTIONS ==============
    
    /**
     * @notice Register a courier
     * @param _courier Courier's wallet address
     */
    function registerCourier(address _courier) external onlyRole(ADMIN_ROLE) {
        require(_courier != address(0), "Invalid address");
        grantRole(COURIER_ROLE, _courier);
        emit CourierRegistered(_courier, block.timestamp);
    }
    
    /**
     * @notice Remove a courier
     * @param _courier Courier's wallet address
     */
    function removeCourier(address _courier) external onlyRole(ADMIN_ROLE) {
        revokeRole(COURIER_ROLE, _courier);
        emit CourierRemoved(_courier, block.timestamp);
    }
    
    /**
     * @notice Register an auditor (for dispute resolution)
     * @param _auditor Auditor's wallet address
     */
    function registerAuditor(address _auditor) external onlyRole(ADMIN_ROLE) {
        require(_auditor != address(0), "Invalid address");
        grantRole(AUDITOR_ROLE, _auditor);
    }
    
    /**
     * @notice Check if address is a courier
     * @param _address Address to check
     */
    function isCourier(address _address) external view returns (bool) {
        return hasRole(COURIER_ROLE, _address);
    }
    
    /**
     * @notice Get total number of proofs
     */
    function getTotalProofs() external view returns (uint256) {
        return _proofIdCounter;
    }
    
    /**
     * @notice Get total number of disputes
     */
    function getTotalDisputeCount() external view returns (uint256) {
        return _disputeIdCounter;
    }
}
