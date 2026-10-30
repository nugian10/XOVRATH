// Deploy XovrathNFT v2 (Nomio model) to BNB Testnet (97) or Mainnet (56).
//
// Usage (from ~/workspace/projects/xovrath):
//   cp .env.example .env   # then fill it in — NEVER paste a private key in chat
//   npx hardhat run scripts/deploy.js --network bscTestnet
//   npx hardhat run scripts/deploy.js --network bsc        # MAINNET, real BNB
//
// The deployer pays gas only. Owner / revenue / agentIdRegistry are
// constructor arguments — the deployer address does NOT have to be
// the owner. FOR XOVRATH (decided by Nugraha 30 Okt 2026 20:31 WIB,
// reversing the 19:10 all-Agentic instruction — same pattern as
// Mythora / MythRealm / MINTFORM):
//   OWNER_ADDRESS    = My Wallet (also the deployer)
//   REVENUE_WALLET   = Binance Agentic Wallet
//   AGENT_ID_REGISTRY = SPACE ID .ai NFT (public registry, verified
//                      on-chain 30 Okt 2026 — the Agentic Wallet
//                      holds 1 Agent ID there)
//                      0x60B9262456dE011F7d15a54CdD8c48bAaa8B022F
// Consequence: after deploy, owner calls (setMintActive /
// setBaseURI / withdraw / setAgentIdRegistry) are made by My Wallet
// from a browser wallet. The Agentic Wallet only receives mint
// proceeds via withdraw(). The deploy transaction is signed by
// My Wallet (the deployer, pays gas).
// Minting (v2, Nomio model): mint() takes no arguments, mints 1,
// requires the minter to hold a SPACE ID .ai Agent ID (no per-wallet
// limit), value must equal currentPrice() exactly.
// See contracts/XovrathNFT.sol header.
const fs = require("node:fs");
const path = require("node:path");
const { ethers } = require("hardhat");

const DEFAULT_AGENT_ID_REGISTRY = "0x60B9262456dE011F7d15a54CdD8c48bAaa8B022F";

async function main() {
  const network = await ethers.provider.getNetwork();
  const [deployer] = await ethers.getSigners();
  const owner = process.env.OWNER_ADDRESS || "";
  const revenue = process.env.REVENUE_WALLET || "";
  const agentIdRegistry = process.env.AGENT_ID_REGISTRY || DEFAULT_AGENT_ID_REGISTRY;
  const baseURI = process.env.BASE_URI || "";

  if (!ethers.isAddress(owner)) throw new Error("OWNER_ADDRESS belum diisi / tidak valid di .env");
  if (!ethers.isAddress(revenue)) throw new Error("REVENUE_WALLET belum diisi / tidak valid di .env");
  if (!ethers.isAddress(agentIdRegistry)) throw new Error("AGENT_ID_REGISTRY tidak valid di .env");
  if (!baseURI.endsWith("/")) throw new Error("BASE_URI harus diakhiri '/' dan menunjuk folder metadata IPFS, contoh ipfs://<CID>/");

  console.log("Network:", network.name, "chainId:", Number(network.chainId));
  console.log("Deployer (bayar gas):", deployer.address);
  console.log("Owner:", owner);
  console.log("Revenue wallet:", revenue);
  console.log("Agent ID registry:", agentIdRegistry);
  console.log("Base URI:", baseURI);
  if (Number(network.chainId) === 56) {
    console.log("!!! MAINNET — BNB SUNGGUHAN, deploy tidak bisa dibatalkan. Periksa alamat di atas sekali lagi.");
  }

  const Factory = await ethers.getContractFactory("XovrathNFT");
  const contract = await Factory.deploy(owner, revenue, agentIdRegistry, baseURI);
  await contract.waitForDeployment();
  const address = await contract.getAddress();
  console.log("XovrathNFT deployed:", address);
  console.log("MAX_SUPPLY:", (await contract.MAX_SUPPLY()).toString());
  console.log("TIER_1_END:", (await contract.TIER_1_END()).toString());
  console.log("priceTier1:", ethers.formatEther(await contract.priceTier1()), "BNB");
  console.log("priceTier2:", ethers.formatEther(await contract.priceTier2()), "BNB");
  console.log("currentPrice:", ethers.formatEther(await contract.currentPrice()), "BNB");
  console.log("mintActive:", await contract.mintActive());
  console.log("agentIdCheckRequired:", await contract.agentIdCheckRequired());
  console.log("BscScan:", `https://bscscan.com/address/${address}`);

  const outDir = path.join(__dirname, "..", "deployments");
  fs.mkdirSync(outDir, { recursive: true });
  const out = path.join(outDir, `xovrath-${Number(network.chainId)}.json`);
  fs.writeFileSync(
    out,
    JSON.stringify(
      {
        network: network.name,
        chainId: Number(network.chainId),
        address,
        owner,
        revenueWallet: revenue,
        agentIdRegistry,
        baseURI,
        maxSupply: 2222,
        tier1End: 500,
        priceTier1: "0.0002",
        priceTier2: "0.0008",
        mintActive: false,
        agentIdCheckRequired: true,
        model: "nomio-v2",
      },
      null,
      2
    )
  );
  console.log("Saved:", out);
  console.log("Langkah berikut: verifikasi source di BscScan, lalu setBaseURI (kalau IPFS belum siap), setMintActive(true) HANYA saat launch.");
}

main().catch((err) => {
  console.error(err);
  process.exitCode = 1;
});
