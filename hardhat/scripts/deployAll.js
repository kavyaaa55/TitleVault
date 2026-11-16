require("dotenv").config();
const hre = require("hardhat");

async function main() {
  const [deployer] = await hre.ethers.getSigners();
  const registrar = process.env.REGISTRAR_ADDRESS || deployer.address;

  console.log("\n========================================");
  console.log("🚀 Deploying All TitleVault Smart Contracts");
  console.log("👤 Deployer Address :", deployer.address);
  console.log("🖊️  Registrar Address:", registrar);
  console.log("🌐 Network          :", hre.network.name);
  console.log("========================================\n");

  // 1. RegistryResolver
  console.log("⏳ Deploying RegistryResolver...");
  const RegistryResolver = await hre.ethers.getContractFactory("RegistryResolver", deployer);
  const resolver = await RegistryResolver.deploy(registrar);
  await resolver.waitForDeployment();
  const resolverAddress = await resolver.getAddress();
  console.log("✅ RegistryResolver deployed at:", resolverAddress);

  // 2. AgreementLedger
  console.log("\n⏳ Deploying AgreementLedger...");
  const AgreementLedger = await hre.ethers.getContractFactory("AgreementLedger", deployer);
  const agreementLedger = await AgreementLedger.deploy(deployer.address);
  await agreementLedger.waitForDeployment();
  const ledgerAddress = await agreementLedger.getAddress();
  console.log("✅ AgreementLedger deployed at:", ledgerAddress);

  const ledgerRole = await agreementLedger.REGISTRAR_ROLE();
  const grantLedgerTx = await agreementLedger.grantRole(ledgerRole, registrar);
  await grantLedgerTx.wait();
  console.log("🔑 REGISTRAR_ROLE granted to registrar on AgreementLedger");

  // 3. AgreementMerkleAnchor
  console.log("\n⏳ Deploying AgreementMerkleAnchor...");
  const AgreementMerkleAnchor = await hre.ethers.getContractFactory("AgreementMerkleAnchor", deployer);
  const anchor = await AgreementMerkleAnchor.deploy(deployer.address);
  await anchor.waitForDeployment();
  const anchorAddress = await anchor.getAddress();
  console.log("✅ AgreementMerkleAnchor deployed at:", anchorAddress);

  const anchorRole = await anchor.REGISTRAR_ROLE();
  const grantAnchorTx = await anchor.grantRole(anchorRole, registrar);
  await grantAnchorTx.wait();
  console.log("🔑 REGISTRAR_ROLE granted to registrar on AgreementMerkleAnchor");

  // 4. RegistryRootAnchor
  console.log("\n⏳ Deploying RegistryRootAnchor...");
  const RootAnchor = await hre.ethers.getContractFactory("RegistryRootAnchor", deployer);
  const rootAnchor = await RootAnchor.deploy(registrar);
  await rootAnchor.waitForDeployment();
  const rootAnchorAddress = await rootAnchor.getAddress();
  console.log("✅ RegistryRootAnchor deployed at:", rootAnchorAddress);

  console.log("\n========================================");
  console.log("🎉 ALL CONTRACTS DEPLOYED SUCCESSFULLY");
  console.log("========================================");
  console.log("RegistryResolver             :", resolverAddress);
  console.log("AgreementLedger              :", ledgerAddress);
  console.log("AgreementMerkleAnchor        :", anchorAddress);
  console.log("RegistryRootAnchor           :", rootAnchorAddress);
  console.log("========================================\n");
}

main().catch((error) => {
  console.error("❌ Deployment failed:", error);
  process.exit(1);
});
