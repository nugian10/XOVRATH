// XOVRATH — site configuration.
// Contract DEPLOYED 30 Okt 2026 20:54 WIB (tx 0x21a8987d...6c70fb):
//   0x12a7f54990fd7ce6c2dabeb3df3de75fb812f3a1
// Owner = My Wallet, revenue = Agentic Wallet. Never fill in a guessed address.
const XOVRATH_CONFIG = {
  CONTRACT_ADDRESS: "0x12a7f54990fd7ce6c2dabeb3df3de75fb812f3a1",
  CHAIN_ID: 56,
  CHAIN_NAME: "BNB Smart Chain Mainnet",
  TOTAL_SUPPLY: 2222,
  // Storage is GitHub (chosen 30 Okt 2026), not IPFS.
  // Vercel deploys only this site/ folder, so ../collection/ paths do
  // NOT exist on the live site — everything below points at the files
  // in the public GitHub repo instead (fixed 30 Okt 2026: gallery was
  // empty because the old ../collection/ paths returned 404).
  IMAGES_BASE: "https://raw.githubusercontent.com/nugian10/XOVRATH/main/collection/images/",
  METADATA_BASE: "https://raw.githubusercontent.com/nugian10/XOVRATH/main/collection/metadata/",
  COLLECTION_JSON: "https://raw.githubusercontent.com/nugian10/XOVRATH/main/collection/collection.json",
  ALL_TOKENS_JSON: "https://raw.githubusercontent.com/nugian10/XOVRATH/main/collection/all-tokens.json",
  IMAGE_PATH: (id) => `https://raw.githubusercontent.com/nugian10/XOVRATH/main/collection/images/${id}.svg`,
  METADATA_PATH: (id) => `https://raw.githubusercontent.com/nugian10/XOVRATH/main/collection/metadata/${id}.json`,
  CLASSIFICATIONS: ["VOID", "DISTORTION", "ORIGIN", "ANOMALY", "FRACTURE", "UNKNOWN"],
};
