// XOVRATH — site configuration.
// The contract is NOT deployed. CONTRACT_ADDRESS stays empty until the
// owner deploys XovrathNFT.sol on BNB Smart Chain Mainnet (56) and
// records the real address here. Never fill in a guessed address.
const XOVRATH_CONFIG = {
  CONTRACT_ADDRESS: "",
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
