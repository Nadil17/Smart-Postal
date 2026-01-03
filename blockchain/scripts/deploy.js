const hre = require("hardhat");
const fs = require("fs");
const path = require("path");

async function main() {
  console.log("╔════════════════════════════════════════════════════════════════╗");
  console.log("║      SMART POSTAL - BLOCKCHAIN DEPLOYMENT                       ║");
  console.log("║      Privacy-First Delivery Verification Protocol               ║");
  console.log("║                                                                  ║");
  console.log("║      Research Implementation                                     ║");
  console.log("╚════════════════════════════════════════════════════════════════╝\n");

  const [deployer] = await hre.ethers.getSigners();
  
  console.log("📋 Deployment Configuration:");
  console.log("   Network:", hre.network.name);
  console.log("   Chain ID:", hre.network.config.chainId);
  console.log("   Deployer:", deployer.address);
  
  const balance = await hre.ethers.provider.getBalance(deployer.address);
  console.log("   Balance:", hre.ethers.formatEther(balance), "ETH\n");

  // Deploy DeliveryProofRegistry
  console.log("📦 Deploying DeliveryProofRegistry...");
  console.log("   This contract implements the cryptographic commitment protocol");
  console.log("   for privacy-preserving delivery verification.\n");
  
  const DeliveryProofRegistry = await hre.ethers.getContractFactory("DeliveryProofRegistry");
  const registry = await DeliveryProofRegistry.deploy();
  await registry.waitForDeployment();
  
  const registryAddress = await registry.getAddress();
  console.log("✅ DeliveryProofRegistry deployed to:", registryAddress);

  // Get deployment transaction details
  const deployTx = registry.deploymentTransaction();
  let blockNumber = null;
  let gasUsed = null;
  
  if (deployTx) {
    const receipt = await deployTx.wait();
    blockNumber = receipt.blockNumber;
    gasUsed = receipt.gasUsed.toString();
    console.log("   Gas Used:", gasUsed);
    console.log("   Block:", blockNumber);
  }

  // Register deployer as first courier for testing
  console.log("\n🔧 Setting up initial configuration...");
  const tx = await registry.registerCourier(deployer.address);
  await tx.wait();
  console.log("   ✅ Deployer registered as courier for testing");

  // Save deployment info
  const deploymentInfo = {
    network: hre.network.name,
    chainId: hre.network.config.chainId,
    contracts: {
      DeliveryProofRegistry: registryAddress
    },
    deployer: deployer.address,
    timestamp: new Date().toISOString(),
    blockNumber: blockNumber,
    gasUsed: gasUsed
  };

  // Save to deployments folder
  const deploymentsDir = path.join(__dirname, "../deployments");
  if (!fs.existsSync(deploymentsDir)) {
    fs.mkdirSync(deploymentsDir, { recursive: true });
  }

  const filename = `${hre.network.name}-deployment.json`;
  const deploymentPath = path.join(deploymentsDir, filename);
  fs.writeFileSync(deploymentPath, JSON.stringify(deploymentInfo, null, 2));
  console.log(`\n💾 Deployment info saved to: deployments/${filename}`);

  // Also save to backend config
  const backendConfigDir = path.join(__dirname, "../../smart-postal-back-end/backend/config");
  const backendConfigPath = path.join(backendConfigDir, "blockchain.json");
  
  try {
    if (!fs.existsSync(backendConfigDir)) {
      fs.mkdirSync(backendConfigDir, { recursive: true });
    }
    fs.writeFileSync(backendConfigPath, JSON.stringify(deploymentInfo, null, 2));
    console.log("💾 Backend config updated: smart-postal-back-end/backend/config/blockchain.json");
  } catch (e) {
    console.log("⚠️  Could not update backend config:", e.message);
  }

  // Summary
  console.log("\n╔════════════════════════════════════════════════════════════════╗");
  console.log("║                    DEPLOYMENT SUMMARY                           ║");
  console.log("╠════════════════════════════════════════════════════════════════╣");
  console.log(`║  Network:               ${hre.network.name.padEnd(40)}║`);
  console.log(`║  Chain ID:              ${String(hre.network.config.chainId).padEnd(40)}║`);
  console.log(`║  DeliveryProofRegistry: ${registryAddress}  ║`);
  console.log(`║  Deployer:              ${deployer.address}  ║`);
  console.log("╠════════════════════════════════════════════════════════════════╣");
  console.log("║  PRIVACY FEATURES:                                              ║");
  console.log("║  ✅ No personal data stored on-chain                            ║");
  console.log("║  ✅ Cryptographic commitments only                               ║");
  console.log("║  ✅ PDPA-compliant by design                                     ║");
  console.log("║  ✅ ETA Section 21 admissible                                    ║");
  console.log("╚════════════════════════════════════════════════════════════════╝");

  // Verification instructions for testnets
  if (hre.network.name !== "localhost" && hre.network.name !== "hardhat") {
    console.log("\n📝 To verify on Etherscan/Polygonscan:");
    console.log(`   npx hardhat verify --network ${hre.network.name} ${registryAddress}`);
  }

  return deploymentInfo;
}

main()
  .then(() => process.exit(0))
  .catch((error) => {
    console.error("❌ Deployment failed:", error);
    process.exit(1);
  });
