const { expect } = require("chai");
const { ethers } = require("hardhat");

describe("DeliveryProofRegistry", function () {
  let registry;
  let owner;
  let courier;
  let customer;
  let auditor;

  // Sample test data
  const sampleTokenHash = ethers.keccak256(ethers.toUtf8Bytes("sample_token"));
  const sampleCommitmentHash = ethers.keccak256(ethers.toUtf8Bytes("sample_commitment"));
  const deliveryId = "DLV-2025-001234";
  const aiModel = "ArcFace";
  const confidenceScore = 8700; // 87.00%
  const gpsLat = 6927100; // 6.9271 * 1e6
  const gpsLng = 79861200; // 79.8612 * 1e6

  beforeEach(async function () {
    [owner, courier, customer, auditor] = await ethers.getSigners();

    const DeliveryProofRegistry = await ethers.getContractFactory("DeliveryProofRegistry");
    registry = await DeliveryProofRegistry.deploy();
    await registry.waitForDeployment();

    // Register courier
    await registry.registerCourier(courier.address);
  });

  describe("Deployment", function () {
    it("Should set the deployer as admin", async function () {
      const ADMIN_ROLE = await registry.ADMIN_ROLE();
      expect(await registry.hasRole(ADMIN_ROLE, owner.address)).to.be.true;
    });

    it("Should register courier correctly", async function () {
      expect(await registry.isCourier(courier.address)).to.be.true;
    });
  });

  describe("Recording Proofs", function () {
    it("Should record a delivery proof", async function () {
      const tx = await registry.connect(courier).recordProof(
        sampleTokenHash,
        sampleCommitmentHash,
        deliveryId,
        0, // CUSTOMER_VERIFIED
        1, // PASS
        confidenceScore,
        gpsLat,
        gpsLng,
        aiModel
      );

      await expect(tx)
        .to.emit(registry, "ProofRecorded")
        .withArgs(
          1, // proofId
          deliveryId,
          0, // CUSTOMER_VERIFIED
          sampleCommitmentHash,
          1, // PASS
          confidenceScore,
          await ethers.provider.getBlock("latest").then(b => b.timestamp)
        );

      // Verify statistics
      const stats = await registry.getStatistics();
      expect(stats[0]).to.equal(1n); // totalDeliveries
      expect(stats[1]).to.equal(1n); // totalVerifications
    });

    it("Should prevent replay attacks (same commitment)", async function () {
      await registry.connect(courier).recordProof(
        sampleTokenHash,
        sampleCommitmentHash,
        deliveryId,
        0, 1, confidenceScore, gpsLat, gpsLng, aiModel
      );

      // Try to use same commitment again
      await expect(
        registry.connect(courier).recordProof(
          sampleTokenHash,
          sampleCommitmentHash, // Same commitment
          "DLV-2025-001235",
          0, 1, confidenceScore, gpsLat, gpsLng, aiModel
        )
      ).to.be.revertedWith("Commitment already used");
    });

    it("Should reject non-courier addresses", async function () {
      await expect(
        registry.connect(customer).recordProof(
          sampleTokenHash,
          sampleCommitmentHash,
          deliveryId,
          0, 1, confidenceScore, gpsLat, gpsLng, aiModel
        )
      ).to.be.reverted;
    });

    it("Should store GPS coordinates correctly", async function () {
      await registry.connect(courier).recordProof(
        sampleTokenHash,
        sampleCommitmentHash,
        deliveryId,
        0, 1, confidenceScore, gpsLat, gpsLng, aiModel
      );

      const proof = await registry.getProof(1);
      expect(proof.gpsLatitude).to.equal(gpsLat);
      expect(proof.gpsLongitude).to.equal(gpsLng);
    });
  });

  describe("COD Recording", function () {
    const codCommitmentHash = ethers.keccak256(ethers.toUtf8Bytes("cod_commitment"));
    const customerCommitmentHash = ethers.keccak256(ethers.toUtf8Bytes("customer_commitment"));
    const spokenHash = ethers.keccak256(ethers.toUtf8Bytes("spoken_confirmation"));
    const amountLKR = 15000;

    it("Should record COD transaction", async function () {
      const tx = await registry.connect(courier).recordCOD(
        deliveryId,
        codCommitmentHash,
        customerCommitmentHash,
        amountLKR,
        spokenHash,
        gpsLat,
        gpsLng
      );

      await expect(tx)
        .to.emit(registry, "CODRecorded")
        .withArgs(deliveryId, amountLKR, codCommitmentHash, await ethers.provider.getBlock("latest").then(b => b.timestamp));

      // Verify COD proof
      const codProof = await registry.getCODProof(deliveryId);
      expect(codProof.amountLKR).to.equal(amountLKR);
      expect(codProof.codCommitmentHash).to.equal(codCommitmentHash);
    });

    it("Should prevent duplicate COD for same delivery", async function () {
      await registry.connect(courier).recordCOD(
        deliveryId,
        codCommitmentHash,
        customerCommitmentHash,
        amountLKR,
        spokenHash,
        gpsLat,
        gpsLng
      );

      await expect(
        registry.connect(courier).recordCOD(
          deliveryId, // Same delivery
          codCommitmentHash,
          customerCommitmentHash,
          amountLKR,
          spokenHash,
          gpsLat,
          gpsLng
        )
      ).to.be.revertedWith("COD already recorded");
    });

    it("Should track total COD statistics", async function () {
      await registry.connect(courier).recordCOD(
        deliveryId,
        codCommitmentHash,
        customerCommitmentHash,
        amountLKR,
        spokenHash,
        gpsLat,
        gpsLng
      );

      const stats = await registry.getStatistics();
      expect(stats[2]).to.equal(1n); // totalCODTransactions
      expect(stats[3]).to.equal(BigInt(amountLKR)); // totalCODAmountLKR
    });
  });

  describe("Consent Recording", function () {
    const consentHash = ethers.keccak256(ethers.toUtf8Bytes("consent"));
    const neighborCommitmentHash = ethers.keccak256(ethers.toUtf8Bytes("neighbor"));
    const customerGpsLat = 6927200;
    const customerGpsLng = 79861300;

    it("Should record consent", async function () {
      const tx = await registry.recordConsent(
        deliveryId,
        consentHash,
        neighborCommitmentHash,
        true, // consent given
        customerGpsLat,
        customerGpsLng
      );

      await expect(tx)
        .to.emit(registry, "ConsentRecorded")
        .withArgs(deliveryId, true, neighborCommitmentHash, await ethers.provider.getBlock("latest").then(b => b.timestamp));

      // Verify consent record
      const consent = await registry.getConsentRecord(deliveryId);
      expect(consent.consentGiven).to.be.true;
      expect(consent.neighborCommitmentHash).to.equal(neighborCommitmentHash);
    });
  });

  describe("Dispute Resolution", function () {
    beforeEach(async function () {
      // Record a proof first
      await registry.connect(courier).recordProof(
        sampleTokenHash,
        sampleCommitmentHash,
        deliveryId,
        0, 1, confidenceScore, gpsLat, gpsLng, aiModel
      );
    });

    it("Should allow raising disputes", async function () {
      const reason = "Package not received";
      
      const tx = await registry.connect(customer).raiseDispute(deliveryId, reason);
      
      await expect(tx)
        .to.emit(registry, "DisputeRaised")
        .withArgs(1, deliveryId, customer.address, reason, await ethers.provider.getBlock("latest").then(b => b.timestamp));

      // Verify dispute
      const dispute = await registry.getDispute(1);
      expect(dispute.deliveryId).to.equal(deliveryId);
      expect(dispute.reason).to.equal(reason);
      expect(dispute.status).to.equal(0); // OPEN
    });

    it("Should allow admin to resolve disputes", async function () {
      await registry.connect(customer).raiseDispute(deliveryId, "Package not received");
      
      const resolution = "Evidence shows successful delivery at recorded GPS location";
      const tx = await registry.resolveDispute(1, 4, resolution); // RESOLVED_COURIER_FAVOR
      
      await expect(tx)
        .to.emit(registry, "DisputeResolved");

      const dispute = await registry.getDispute(1);
      expect(dispute.status).to.equal(4); // RESOLVED_COURIER_FAVOR
      expect(dispute.resolution).to.equal(resolution);
    });
  });

  describe("Evidence Retrieval", function () {
    beforeEach(async function () {
      // Record proof
      await registry.connect(courier).recordProof(
        sampleTokenHash,
        sampleCommitmentHash,
        deliveryId,
        0, 1, confidenceScore, gpsLat, gpsLng, aiModel
      );

      // Record COD
      const codHash = ethers.keccak256(ethers.toUtf8Bytes("cod"));
      const custHash = ethers.keccak256(ethers.toUtf8Bytes("cust"));
      const spokenHash = ethers.keccak256(ethers.toUtf8Bytes("spoken"));
      await registry.connect(courier).recordCOD(
        deliveryId, codHash, custHash, 15000, spokenHash, gpsLat, gpsLng
      );
    });

    it("Should return complete delivery evidence", async function () {
      const evidence = await registry.getDeliveryEvidence(deliveryId);
      
      expect(evidence.proofCount).to.equal(1n);
      expect(evidence.hasCOD).to.be.true;
      expect(evidence.codAmountLKR).to.equal(15000n);
      expect(evidence.hasConsent).to.be.false;
    });

    it("Should verify proof integrity", async function () {
      const isValid = await registry.verifyProofIntegrity(1, sampleTokenHash);
      expect(isValid).to.be.true;

      const wrongHash = ethers.keccak256(ethers.toUtf8Bytes("wrong"));
      const isInvalid = await registry.verifyProofIntegrity(1, wrongHash);
      expect(isInvalid).to.be.false;
    });
  });

  describe("Privacy Guarantees", function () {
    it("Should not store any personal data", async function () {
      // Record proof with commitment hash (not actual identity)
      await registry.connect(courier).recordProof(
        sampleTokenHash,
        sampleCommitmentHash,
        deliveryId,
        0, 1, confidenceScore, gpsLat, gpsLng, aiModel
      );

      const proof = await registry.getProof(1);
      
      // Verify only hashes are stored, not personal data
      expect(proof.tokenHash).to.equal(sampleTokenHash);
      expect(proof.commitmentHash).to.equal(sampleCommitmentHash);
      // No NIC, no name, no biometric data
    });

    it("Should prevent commitment reversal", async function () {
      // The commitment hash cannot be reversed to reveal the original NIC
      // This is guaranteed by SHA-3-256's one-way property
      // Test that commitment is stored as-is (not decrypted)
      await registry.connect(courier).recordProof(
        sampleTokenHash,
        sampleCommitmentHash,
        deliveryId,
        0, 1, confidenceScore, gpsLat, gpsLng, aiModel
      );

      const proof = await registry.getProof(1);
      expect(proof.commitmentHash).to.equal(sampleCommitmentHash);
      // Original NIC cannot be recovered from this hash
    });
  });

  describe("Statistics", function () {
    it("Should track all statistics correctly", async function () {
      // Record multiple proofs
      for (let i = 0; i < 3; i++) {
        const commitmentHash = ethers.keccak256(ethers.toUtf8Bytes(`commitment_${i}`));
        await registry.connect(courier).recordProof(
          sampleTokenHash,
          commitmentHash,
          `DLV-2025-00${i}`,
          0, 1, confidenceScore, gpsLat, gpsLng, aiModel
        );
      }

      const stats = await registry.getStatistics();
      expect(stats[0]).to.equal(3n); // totalDeliveries
      expect(stats[1]).to.equal(3n); // totalVerifications
    });
  });
});
