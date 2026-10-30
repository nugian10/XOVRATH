// SPDX-License-Identifier: MIT
pragma solidity 0.8.24;

// ============================================================
// XOVRATH v2 — Unknown Artifacts
// ERC-721, BNB Smart Chain Mainnet (Chain ID 56)
// ------------------------------------------------------------
// v2 REBUILDS the contract on the Nomio model (nomio.uk),
// replacing v1 (archived at archive/XovrathNFT-v1-eip712.sol,
// EIP-712 agent-signature auth). What changed and why:
//
// FROM NOMIO (verified on-chain 2026-10-30, not copied blindly):
// - mint() takes NO arguments and mints exactly 1 token.
//   Nomio's mint selector is 0x1249c58b == keccak("mint()")[:4],
//   confirmed against its deployed contract 0x48b5e5573e76CaAa41a893496dE6C857720E6b40
//   (name "Nomio", totalSupply 2,559 at check time, currentPrice
//   0.00027 BNB). XOVRATH keeps its own supply and prices.
// - Agent-only is enforced ON-CHAIN by an Agent ID check, not by
//   an off-chain signature: the minter must hold a SPACE ID .ai
//   Agent ID NFT. The check is IERC721(agentIdRegistry)
//   .balanceOf(msg.sender) > 0, reverting with NoAgentId.
//   The registry is the public SPACE ID .ai NFT contract on BSC:
//     0x60B9262456dE011F7d15a54CdD8c48bAaa8B022F
//   Verified on-chain 2026-10-30: the contract exists (8,756
//   bytes of runtime code), and Nugraha's Binance Agentic Wallet
//   0x89c37649Ba3BAA9E1ce028612b7DE4e9c3a947B7 holds exactly 1
//   Agent ID, while his My Wallet 0x0262... holds 0. The same
//   mechanism is used by AnthroBit and Spoxy on BNB Chain.
// - currentPrice() returns the price of the NEXT token to mint.
//   The agent reads it and sends exactly that value.
// - NO per-wallet limit (reversal 30 Okt 2026 19:28 WIB: "Jangan
//   kasih batasan untuk mint perwallet"). Nomio's one-work-per-
//   wallet rule was adopted in v2 first, then removed on the
//   user's order — it also restores the master prompt's rule and
//   his standing preference (Mythora: all mint limits removed
//   29 Okt 2026). Any wallet holding an Agent ID may call mint()
//   as many times as it likes, one token per call, paying
//   currentPrice() each time. One wallet CAN therefore buy up
//   a large share of the supply — that is the accepted trade-off.
// - The seed is stored on-chain at mint: tokenSeed[tokenId] =
//   keccak256(blockhash(block.number - 1), minter, tokenId).
//   It is emitted in Minted and is the mint's on-chain fingerprint.
//   HONEST LIMIT: unlike Nomio, whose artwork is drawn from the
//   seed, XOVRATH's artwork is pre-generated per token ID (2,222
//   deterministic SVGs in collection/). The seed does NOT change
//   the artwork — it proves which block and wallet minted it.
//
// KEPT FROM XOVRATH (not Nomio's):
// - Supply 2,222, token IDs 1–2,222 sequential.
// - Two-tier pricing, computed ON-CHAIN per token ID:
//     Token IDs   1–500 : 0.0002 BNB each  (Early Mint)
//     Token IDs 501–2222: 0.0008 BNB each  (Standard Mint)
//   currentPrice() is the price of the next ID, so the tier
//   boundary is crossed automatically as supply grows.
//   Payment must equal currentPrice() exactly — underpayment
//   and overpayment are both rejected.
// - Tier prices configurable by the owner ONLY before the first
//   mint (setTierPrices reverts once totalSupply > 0). The
//   boundary (500) is a constant and can never be moved.
// - Calls from contracts are rejected (NoContracts): only an
//   EOA wallet holding an Agent ID can mint, as on Nomio.
// - Owner / revenue are CONSTRUCTOR PARAMETERS — no wallet
//   address is hard-coded except the public Agent ID registry
//   default. FOR XOVRATH (forced by Nugraha 30 Okt 2026):
//     owner         = Binance Agentic Wallet
//     revenueWallet = Binance Agentic Wallet
//     (both: 0x89c37649Ba3BAA9E1ce028612b7DE4e9c3a947B7)
//   Consequence: owner calls (setMintActive / setBaseURI /
//   withdraw / setAgentIdRegistry / setTierPrices) can ONLY be
//   made by that wallet's own paired Binance agent — a browser
//   wallet cannot sign for them. The deploy transaction itself
//   is still signed by a separate funded deployer wallet.
// - Funds: mint payments stay in this contract until the owner
//   calls withdraw(), which sends the whole balance to the
//   revenue wallet.
//
// ESCAPE HATCH (documented, on-chain, visible):
//   agentIdCheckRequired defaults to true. The owner can turn
//   the Agent ID check off (setAgentIdCheckRequired(false)) or
//   point it at a different registry (setAgentIdRegistry).
//   Turning it off makes minting permissionless on-chain and
//   agent-only in the UI only (the Mythora pattern). Do not
//   hide such a change.
//
// This contract is SOURCE-VERIFIABLE on BscScan. It is NOT
// an independent audit — keep that disclosure on the site.
// ============================================================

import "@openzeppelin/contracts/token/ERC721/ERC721.sol";
import "@openzeppelin/contracts/token/ERC721/IERC721.sol";
import "@openzeppelin/contracts/access/Ownable.sol";
import "@openzeppelin/contracts/utils/ReentrancyGuard.sol";
import "@openzeppelin/contracts/utils/Strings.sol";

contract XovrathNFT is ERC721, Ownable, ReentrancyGuard {
    using Strings for uint256;

    uint256 public constant MAX_SUPPLY = 2222;
    uint256 public constant TIER_1_END = 500;

    // Default tier prices (BNB). Changeable by owner only
    // before the first mint — see setTierPrices().
    uint256 public constant DEFAULT_PRICE_TIER_1 = 0.0002 ether;
    uint256 public constant DEFAULT_PRICE_TIER_2 = 0.0008 ether;

    /// @notice SPACE ID .ai Agent ID NFT on BNB Smart Chain.
    /// Public registry used by Nomio / AnthroBit / Spoxy.
    address public constant DEFAULT_AGENT_ID_REGISTRY =
        0x60B9262456dE011F7d15a54CdD8c48bAaa8B022F;

    uint256 public priceTier1 = DEFAULT_PRICE_TIER_1;
    uint256 public priceTier2 = DEFAULT_PRICE_TIER_2;

    bool public mintActive;
    address public revenueWallet;
    address public agentIdRegistry;
    bool public agentIdCheckRequired = true;

    string private _baseTokenURI;
    uint256 private _nextTokenId = 1;

    /// @dev On-chain mint seed per token (Nomio rule).
    mapping(uint256 => bytes32) public tokenSeed;

    event Minted(address indexed minter, uint256 indexed tokenId, uint256 price, bytes32 seed);
    event MintActiveChanged(bool active);
    event BaseURIUpdated(string baseURI);
    event RevenueWalletUpdated(address indexed revenueWallet);
    event AgentIdRegistryUpdated(address indexed agentIdRegistry);
    event AgentIdCheckChanged(bool required);
    event TierPricesUpdated(uint256 priceTier1, uint256 priceTier2);
    event Withdrawn(address indexed revenueWallet, uint256 amount);

    error MintInactive();
    error ExceedsMaxSupply();
    error SoldOut();
    error IncorrectPayment(uint256 expected, uint256 received);
    error InvalidAddress();
    error NoFunds();
    error NoAgentId();
    error NoContracts();
    error PricesLocked();
    error InvalidPrice();

    constructor(
        address initialOwner,
        address revenueWallet_,
        address agentIdRegistry_,
        string memory baseURI_
    ) ERC721("XOVRATH", "XOVR") Ownable(initialOwner) {
        if (initialOwner == address(0) || revenueWallet_ == address(0) || agentIdRegistry_ == address(0)) {
            revert InvalidAddress();
        }
        revenueWallet = revenueWallet_;
        agentIdRegistry = agentIdRegistry_;
        _baseTokenURI = baseURI_;
    }

    // ---------- supply / pricing (read-only, for UI + agents) ----------

    function totalSupply() public view returns (uint256) {
        return _nextTokenId - 1;
    }

    function nextTokenId() public view returns (uint256) {
        return _nextTokenId;
    }

    /// @notice Price of a single token ID. Reverts outside 1..MAX_SUPPLY.
    function priceForTokenId(uint256 tokenId) public view returns (uint256) {
        if (tokenId == 0 || tokenId > MAX_SUPPLY) revert ExceedsMaxSupply();
        if (tokenId <= TIER_1_END) return priceTier1;
        return priceTier2;
    }

    /// @notice Price of the next NFT to be minted (Nomio's
    /// currentPrice). Reverts when sold out. The agent reads
    /// this and sends exactly this value with mint().
    function currentPrice() public view returns (uint256) {
        if (_nextTokenId > MAX_SUPPLY) revert SoldOut();
        return priceForTokenId(_nextTokenId);
    }

    /// @notice Alias of currentPrice() for agents written
    /// against the v1 interface.
    function getMintPrice() public view returns (uint256) {
        return currentPrice();
    }

    /// @notice True when `wallet` holds at least one SPACE ID
    /// .ai Agent ID NFT in the configured registry. A registry
    /// that does not answer like an ERC-721 returns false
    /// instead of reverting, so a bad registry address can
    /// never brick reads — it only blocks minting.
    /// Implemented with a low-level staticcall on purpose: a
    /// high-level balanceOf call to an address with no code
    /// returns empty data, and the ABI decoder reverts on
    /// empty returndata OUTSIDE try/catch. The low-level call
    /// returns ok=false / short data instead, which we map
    /// to false here.
    function hasAgentId(address wallet) public view returns (bool) {
        if (agentIdRegistry == address(0)) return false;
        (bool ok, bytes memory data) = agentIdRegistry.staticcall(
            abi.encodeWithSelector(IERC721.balanceOf.selector, wallet)
        );
        if (!ok || data.length < 32) return false;
        return abi.decode(data, (uint256)) > 0;
    }

    // ---------- minting (Nomio model) ----------

    /// @notice Mint exactly ONE XOVRATH to msg.sender.
    /// No arguments — the token ID is the next sequential one.
    /// Requires, in order: mint active; caller is not a contract;
    /// caller holds an Agent ID (unless the check is disabled);
    /// supply remains; msg.value equals currentPrice() exactly.
    /// No per-wallet limit: the same wallet may call mint()
    /// again for another token. Stores the mint seed.
    function mint() external payable nonReentrant {
        if (!mintActive) revert MintInactive();
        if (msg.sender.code.length > 0) revert NoContracts();
        if (agentIdCheckRequired && !hasAgentId(msg.sender)) revert NoAgentId();

        uint256 tokenId = _nextTokenId;
        if (tokenId > MAX_SUPPLY) revert SoldOut();
        uint256 price = priceForTokenId(tokenId);
        if (msg.value != price) revert IncorrectPayment(price, msg.value);

        _nextTokenId++;
        bytes32 seed = keccak256(
            abi.encodePacked(blockhash(block.number - 1), msg.sender, tokenId)
        );
        tokenSeed[tokenId] = seed;
        _safeMint(msg.sender, tokenId);
        emit Minted(msg.sender, tokenId, price, seed);
    }

    // ---------- metadata (IPFS) ----------

    function baseURI() public view returns (string memory) {
        return _baseTokenURI;
    }

    /// @notice tokenURI = baseURI + tokenId + ".json", matching the
    /// committed metadata files 1.json .. 2222.json.
    /// The base URI must therefore end with "/" and point at the
    /// folder holding those files on IPFS, e.g.
    /// ipfs://<metadata-CID>/
    function tokenURI(uint256 tokenId) public view override returns (string memory) {
        if (_ownerOf(tokenId) == address(0)) revert ERC721NonexistentToken(tokenId);
        return string.concat(_baseTokenURI, tokenId.toString(), ".json");
    }

    // ---------- owner-only administration ----------

    function setMintActive(bool active) external onlyOwner {
        mintActive = active;
        emit MintActiveChanged(active);
    }

    function setBaseURI(string calldata baseURI_) external onlyOwner {
        _baseTokenURI = baseURI_;
        emit BaseURIUpdated(baseURI_);
    }

    function setRevenueWallet(address revenueWallet_) external onlyOwner {
        if (revenueWallet_ == address(0)) revert InvalidAddress();
        revenueWallet = revenueWallet_;
        emit RevenueWalletUpdated(revenueWallet_);
    }

    /// @notice Point the Agent ID check at a different registry
    /// (e.g. if SPACE ID migrates the .ai NFT contract).
    function setAgentIdRegistry(address agentIdRegistry_) external onlyOwner {
        if (agentIdRegistry_ == address(0)) revert InvalidAddress();
        agentIdRegistry = agentIdRegistry_;
        emit AgentIdRegistryUpdated(agentIdRegistry_);
    }

    /// @notice Turn the on-chain Agent ID check on/off.
    /// Turning it OFF makes minting permissionless on-chain and
    /// agent-only in the UI only (the Mythora pattern). The
    /// change is public on-chain via this event — do not hide it.
    function setAgentIdCheckRequired(bool required) external onlyOwner {
        agentIdCheckRequired = required;
        emit AgentIdCheckChanged(required);
    }

    /// @notice Change tier prices — ONLY before the first mint.
    /// The 500 boundary itself is a constant and cannot move.
    function setTierPrices(uint256 priceTier1_, uint256 priceTier2_) external onlyOwner {
        if (totalSupply() > 0) revert PricesLocked();
        if (priceTier1_ == 0 || priceTier2_ == 0) revert InvalidPrice();
        priceTier1 = priceTier1_;
        priceTier2 = priceTier2_;
        emit TierPricesUpdated(priceTier1_, priceTier2_);
    }

    /// @notice Send the whole contract balance to the revenue wallet.
    /// Owner-only. Mint payments are not forwarded automatically,
    /// so they can never be sent to the wrong address by a mint.
    function withdraw() external onlyOwner nonReentrant {
        uint256 amount = address(this).balance;
        if (amount == 0) revert NoFunds();
        (bool ok, ) = revenueWallet.call{value: amount}("");
        if (!ok) revert("Withdraw failed");
        emit Withdrawn(revenueWallet, amount);
    }
}
