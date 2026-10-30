// SPDX-License-Identifier: MIT
pragma solidity 0.8.24;

// ============================================================
// XOVRATH — Unknown Artifacts
// ERC-721, BNB Smart Chain Mainnet (Chain ID 56)
// ------------------------------------------------------------
// Supply: 2,222 NFTs, token IDs 1–2,222, sequential.
// No per-wallet mint limit. No PFP, no 3D — art lives off-chain
// (IPFS image + metadata); this contract is the authority for
// supply, price, payment and ownership only.
//
// PRICING — computed ON-CHAIN ONLY, per token ID.
// The frontend / agent must never decide or hard-code a price:
// it calls quoteMint() and pays exactly that.
//   Token IDs   1–500 : 0.0002 BNB each  (Early Mint)
//   Token IDs 501–2222: 0.0008 BNB each  (Standard Mint)
// A batch crossing the boundary pays each token at its own
// tier price. Example from the spec:
//   499 minted + mint(3) = #500 @ 0.0002 + #501,#502 @ 0.0008
//   = 0.0018 BNB (excluding gas).
// Underpayment AND overpayment are both rejected (exact payment).
// Tier prices are configurable by the owner ONLY before any
// mint has happened (setTierPrices reverts once totalSupply > 0).
// The boundary (500) is a constant and can never be moved.
//
// AGENT-ONLY MINTING — enforced on-chain by EIP-712 signature.
// When agentAuthRequired is true (default), mint() requires a
// signature from agentSigner over:
//   MintAuthorization(minter, quantity, nonce, deadline)
// The minter is msg.sender (the user's wallet), the quantity
// and a per-wallet nonce are bound into the signature, and the
// deadline prevents stale authorizations. The agent therefore
// authorizes each mint, but the USER's wallet still pays and
// still receives the NFT, and still gives explicit wallet
// approval for the transaction itself. The agent can never
// mint to itself, change the price, or bypass supply/payment
// checks — those are all re-validated here.
//
// IMPORTANT, honest limitation — read before deploy:
//   agentSigner must be an address whose key the minting agent
//   can actually sign EIP-712 messages with. If the user's
//   Binance Agentic Wallet agent cannot produce such a
//   signature, minting with agentAuthRequired=true will be
//   BLOCKED. In that case the owner must call
//   setAgentAuthRequired(false) — agent-only then lives in
//   the website/agent UI only, exactly like Mythora — or set
//   agentSigner to an address the agent CAN sign with.
//   Never set agentSigner to an address nobody controls.
//
// FUNDS: mint payments stay in this contract until the owner
// calls withdraw(), which sends the whole balance to the
// revenue wallet. No funds are sent anywhere else, and no
// mint ever forwards funds automatically.
//
// Owner / revenue / agentSigner are CONSTRUCTOR PARAMETERS —
// no wallet address is hard-coded in this contract. Whoever
// deploys sets them from environment variables (see
// scripts/deploy.js and .env.example). FOR XOVRATH, Nugraha
// FORCED all three roles to his Binance Agentic Wallet
// (30 Okt 2026 19:10 WIB, "jangan gunakan system sebelumnya"
// — NOT the Mythora / MythRealm / MINTFORM pattern where
// owner = My Wallet 0x0262e8e5E4584D8AB840fD950a6E2E0A414d4097):
//   owner         = Binance Agentic Wallet
//   revenueWallet = Binance Agentic Wallet
//   agentSigner   = Binance Agentic Wallet
//   (all three: 0x89c37649Ba3BAA9E1ce028612b7DE4e9c3a947B7)
// Consequence, stated plainly: owner calls (setBaseURI /
// setMintActive / withdraw / setRevenueWallet / setAgentSigner)
// can ONLY be made by that wallet's own paired Binance agent —
// a browser wallet cannot sign for them. If that agent is
// disconnected or cannot sign, those functions are LOCKED until
// it reconnects. The deploy transaction itself is still signed
// by a separate funded deployer wallet: the Agentic Wallet has
// no exportable key and cannot be a Hardhat deployer.
//
// This contract is SOURCE-VERIFIABLE on BscScan. It is NOT
// an independent audit — keep that disclosure on the site.
// ============================================================

import "@openzeppelin/contracts/token/ERC721/ERC721.sol";
import "@openzeppelin/contracts/access/Ownable.sol";
import "@openzeppelin/contracts/utils/ReentrancyGuard.sol";
import "@openzeppelin/contracts/utils/cryptography/EIP712.sol";
import "@openzeppelin/contracts/utils/cryptography/ECDSA.sol";
import "@openzeppelin/contracts/utils/Strings.sol";

contract XovrathNFT is ERC721, Ownable, ReentrancyGuard, EIP712 {
    using Strings for uint256;

    uint256 public constant MAX_SUPPLY = 2222;
    uint256 public constant TIER_1_END = 500;

    // Default tier prices (BNB). Changeable by owner only
    // before the first mint — see setTierPrices().
    uint256 public constant DEFAULT_PRICE_TIER_1 = 0.0002 ether;
    uint256 public constant DEFAULT_PRICE_TIER_2 = 0.0008 ether;

    uint256 public priceTier1 = DEFAULT_PRICE_TIER_1;
    uint256 public priceTier2 = DEFAULT_PRICE_TIER_2;

    bool public mintActive;
    address public revenueWallet;
    address public agentSigner;
    bool public agentAuthRequired = true;

    string private _baseTokenURI;
    uint256 private _nextTokenId = 1;

    /// @dev Per-wallet nonce, bound into every agent signature.
    mapping(address => uint256) public nonces;

    bytes32 private constant MINT_AUTH_TYPEHASH =
        keccak256("MintAuthorization(address minter,uint256 quantity,uint256 nonce,uint256 deadline)");

    event Minted(address indexed minter, uint256 indexed tokenId, uint256 price);
    event MintActiveChanged(bool active);
    event BaseURIUpdated(string baseURI);
    event RevenueWalletUpdated(address indexed revenueWallet);
    event AgentSignerUpdated(address indexed agentSigner);
    event AgentAuthRequiredChanged(bool required);
    event TierPricesUpdated(uint256 priceTier1, uint256 priceTier2);
    event Withdrawn(address indexed revenueWallet, uint256 amount);

    error MintInactive();
    error InvalidQuantity();
    error ExceedsMaxSupply();
    error SoldOut();
    error IncorrectPayment(uint256 expected, uint256 received);
    error InvalidAddress();
    error NoFunds();
    error InvalidAgentSignature();
    error AuthorizationExpired();
    error PricesLocked();

    constructor(
        address initialOwner,
        address revenueWallet_,
        address agentSigner_,
        string memory baseURI_
    ) ERC721("XOVRATH", "XOVR") Ownable(initialOwner) EIP712("XOVRATH", "1") {
        if (initialOwner == address(0) || revenueWallet_ == address(0) || agentSigner_ == address(0)) {
            revert InvalidAddress();
        }
        revenueWallet = revenueWallet_;
        agentSigner = agentSigner_;
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

    /// @notice Price of the next NFT to be minted. Reverts when sold out.
    function getMintPrice() public view returns (uint256) {
        if (_nextTokenId > MAX_SUPPLY) revert SoldOut();
        return priceForTokenId(_nextTokenId);
    }

    /// @notice Exact total BNB for minting `quantity` NFTs from the
    /// next token ID, tier by tier. Reverts on 0 / over-supply.
    /// Arithmetic (no loop): tier-1 count is capped by how many
    /// tier-1 IDs remain, the rest are tier-2.
    function quoteMint(uint256 quantity) public view returns (uint256 total) {
        if (quantity == 0) revert InvalidQuantity();
        if (_nextTokenId + quantity - 1 > MAX_SUPPLY) revert ExceedsMaxSupply();
        uint256 tier1Remaining = _nextTokenId <= TIER_1_END
            ? TIER_1_END - _nextTokenId + 1
            : 0;
        uint256 tier1Count = quantity < tier1Remaining ? quantity : tier1Remaining;
        uint256 tier2Count = quantity - tier1Count;
        total = tier1Count * priceTier1 + tier2Count * priceTier2;
    }

    /// @notice Same as quoteMint, plus the per-token breakdown so a
    /// UI/agent can show every token's own tier price without
    /// computing any price itself.
    function quoteMintDetailed(uint256 quantity)
        public
        view
        returns (uint256[] memory tokenIds, uint256[] memory prices, uint256 total)
    {
        total = quoteMint(quantity);
        tokenIds = new uint256[](quantity);
        prices = new uint256[](quantity);
        for (uint256 i = 0; i < quantity; i++) {
            tokenIds[i] = _nextTokenId + i;
            prices[i] = priceForTokenId(tokenIds[i]);
        }
    }

    /// @notice EIP-712 digest the agent signs for a mint. Exposed so
    /// the agent (and tests) can verify a signature off-chain.
    /// The signed struct is MintAuthorization(minter, quantity,
    /// nonce, deadline) under domain XOVRATH / version 1.
    function mintAuthorizationDigest(
        address minter,
        uint256 quantity,
        uint256 nonce,
        uint256 deadline
    ) public view returns (bytes32) {
        return _hashTypedDataV4(
            keccak256(abi.encode(MINT_AUTH_TYPEHASH, minter, quantity, nonce, deadline))
        );
    }

    // ---------- minting ----------

    /// @notice Mint `quantity` sequential NFTs to msg.sender.
    /// msg.value must equal quoteMint(quantity) exactly.
    /// When agentAuthRequired is true, `signature` must be the
    /// agentSigner's EIP-712 signature over (msg.sender,
    /// quantity, current nonce, deadline), and deadline must not
    /// have passed. When false, signature is ignored.
    /// No per-wallet limit. Each token emits Minted (+ Transfer).
    function mint(uint256 quantity, uint256 deadline, bytes calldata signature)
        external
        payable
        nonReentrant
    {
        if (!mintActive) revert MintInactive();

        if (agentAuthRequired) {
            if (deadline < block.timestamp) revert AuthorizationExpired();
            uint256 nonce = nonces[msg.sender];
            bytes32 digest = mintAuthorizationDigest(msg.sender, quantity, nonce, deadline);
            // tryRecover (not recover): a malformed signature returns an
            // error instead of reverting with an OZ-internal error, so
            // every bad signature surfaces as InvalidAgentSignature.
            (address signer, ECDSA.RecoverError err, ) = ECDSA.tryRecover(digest, signature);
            if (err != ECDSA.RecoverError.NoError || signer != agentSigner) {
                revert InvalidAgentSignature();
            }
            nonces[msg.sender] = nonce + 1;
        }

        uint256 expected = quoteMint(quantity);
        if (msg.value != expected) revert IncorrectPayment(expected, msg.value);

        for (uint256 i = 0; i < quantity; i++) {
            uint256 tokenId = _nextTokenId;
            uint256 price = priceForTokenId(tokenId);
            _nextTokenId++;
            _safeMint(msg.sender, tokenId);
            emit Minted(msg.sender, tokenId, price);
        }
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

    function setAgentSigner(address agentSigner_) external onlyOwner {
        if (agentSigner_ == address(0)) revert InvalidAddress();
        agentSigner = agentSigner_;
        emit AgentSignerUpdated(agentSigner_);
    }

    /// @notice Turn on-chain agent-signature enforcement on/off.
    /// Turning it OFF makes minting permissionless on-chain and
    /// agent-only in the UI only (the Mythora pattern). The change
    /// is public on-chain via this event — do not hide it.
    function setAgentAuthRequired(bool required) external onlyOwner {
        agentAuthRequired = required;
        emit AgentAuthRequiredChanged(required);
    }

    /// @notice Change tier prices — ONLY before the first mint.
    /// The 500 boundary itself is a constant and cannot move.
    function setTierPrices(uint256 priceTier1_, uint256 priceTier2_) external onlyOwner {
        if (totalSupply() > 0) revert PricesLocked();
        if (priceTier1_ == 0 || priceTier2_ == 0) revert InvalidQuantity();
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
