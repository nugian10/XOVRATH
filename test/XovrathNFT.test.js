const { expect } = require("chai");
const { ethers, network } = require("hardhat");
const { anyValue } = require("@nomicfoundation/hardhat-chai-matchers/withArgs");

const TIER1 = ethers.parseEther("0.0002");
const TIER2 = ethers.parseEther("0.0008");
const REAL_REGISTRY = "0x60B9262456dE011F7d15a54CdD8c48bAaa8B022F";

async function deployFixture() {
  const [owner, revenue, alice, bob] = await ethers.getSigners();
  const Mock = await ethers.getContractFactory("MockAgentIdNFT");
  const mock = await Mock.deploy();
  await mock.waitForDeployment();
  const Factory = await ethers.getContractFactory("XovrathNFT");
  const contract = await Factory.deploy(
    owner.address,
    revenue.address,
    await mock.getAddress(),
    "ipfs://bafyTESTmetadata/"
  );
  await contract.waitForDeployment();
  return { contract, mock, owner, revenue, alice, bob };
}

async function giveAgentId(mock, wallet) {
  await mock.mintTo(wallet.address);
}

describe("XovrathNFT v2 (Nomio model)", function () {
  it("has the right name, symbol, supply, tiers, registry and defaults", async function () {
    const { contract, mock, owner, revenue } = await deployFixture();
    expect(await contract.name()).to.equal("XOVRATH");
    expect(await contract.symbol()).to.equal("XOVR");
    expect(await contract.MAX_SUPPLY()).to.equal(2222);
    expect(await contract.TIER_1_END()).to.equal(500);
    expect(await contract.DEFAULT_AGENT_ID_REGISTRY()).to.equal(REAL_REGISTRY);
    expect(await contract.agentIdRegistry()).to.equal(await mock.getAddress());
    expect(await contract.agentIdCheckRequired()).to.equal(true);
    expect(await contract.priceTier1()).to.equal(TIER1);
    expect(await contract.priceTier2()).to.equal(TIER2);
    expect(await contract.priceForTokenId(1)).to.equal(TIER1);
    expect(await contract.priceForTokenId(500)).to.equal(TIER1);
    expect(await contract.priceForTokenId(501)).to.equal(TIER2);
    expect(await contract.priceForTokenId(2222)).to.equal(TIER2);
    expect(await contract.currentPrice()).to.equal(TIER1);
    expect(await contract.getMintPrice()).to.equal(TIER1);
    expect(await contract.mintActive()).to.equal(false);
    expect(await contract.owner()).to.equal(owner.address);
    expect(await contract.revenueWallet()).to.equal(revenue.address);
    expect(await contract.totalSupply()).to.equal(0);
    expect(await contract.nextTokenId()).to.equal(1);
    await expect(contract.priceForTokenId(0)).to.be.revertedWithCustomError(contract, "ExceedsMaxSupply");
    await expect(contract.priceForTokenId(2223)).to.be.revertedWithCustomError(contract, "ExceedsMaxSupply");
  });

  it("refuses mint while inactive", async function () {
    const { contract, mock, alice } = await deployFixture();
    await giveAgentId(mock, alice);
    await expect(contract.connect(alice).mint({ value: TIER1 })).to.be.revertedWithCustomError(
      contract,
      "MintInactive"
    );
  });

  it("rejects mint without an Agent ID (NoAgentId)", async function () {
    const { contract, owner } = await deployFixture();
    await contract.connect(owner).setMintActive(true);
    // alice holds no Agent ID in the mock registry
    await expect(contract.mint({ value: TIER1 })).to.be.revertedWithCustomError(contract, "NoAgentId");
  });

  it("mints token #1 with exact tier-1 price, stores a seed, sets tokenURI", async function () {
    const { contract, mock, owner, alice } = await deployFixture();
    await giveAgentId(mock, alice);
    expect(await contract.hasAgentId(alice.address)).to.equal(true);
    expect(await contract.hasAgentId(owner.address)).to.equal(false);
    await contract.connect(owner).setMintActive(true);
    await expect(contract.connect(alice).mint({ value: TIER1 }))
      .to.emit(contract, "Minted")
      .withArgs(alice.address, 1, TIER1, anyValue);
    expect(await contract.ownerOf(1)).to.equal(alice.address);
    expect(await contract.tokenURI(1)).to.equal("ipfs://bafyTESTmetadata/1.json");
    expect(await contract.totalSupply()).to.equal(1);
    expect(await contract.nextTokenId()).to.equal(2);
    expect(await contract.tokenSeed(1)).to.not.equal(ethers.ZeroHash);
    expect(await contract.currentPrice()).to.equal(TIER1);
  });

  it("has NO per-wallet limit: the same wallet can mint again", async function () {
    const { contract, mock, owner, alice } = await deployFixture();
    await giveAgentId(mock, alice);
    await contract.connect(owner).setMintActive(true);
    await contract.connect(alice).mint({ value: TIER1 });
    await expect(contract.connect(alice).mint({ value: TIER1 }))
      .to.emit(contract, "Minted")
      .withArgs(alice.address, 2, TIER1, anyValue);
    expect(await contract.ownerOf(1)).to.equal(alice.address);
    expect(await contract.ownerOf(2)).to.equal(alice.address);
    expect(await contract.totalSupply()).to.equal(2);
  });

  it("rejects underpayment and overpayment", async function () {
    const { contract, mock, owner, alice } = await deployFixture();
    await giveAgentId(mock, alice);
    await contract.connect(owner).setMintActive(true);
    await expect(contract.connect(alice).mint({ value: TIER1 - 1n })).to.be.revertedWithCustomError(
      contract,
      "IncorrectPayment"
    );
    await expect(contract.connect(alice).mint({ value: TIER1 + 1n })).to.be.revertedWithCustomError(
      contract,
      "IncorrectPayment"
    );
  });

  it("rejects calls from contracts (NoContracts)", async function () {
    const { contract, mock, owner } = await deployFixture();
    const Caller = await ethers.getContractFactory("MockCaller");
    const caller = await Caller.deploy();
    await caller.waitForDeployment();
    // Give the caller contract an Agent ID so the failure is the
    // contract check, not the Agent ID check.
    await mock.mintTo(await caller.getAddress());
    await contract.connect(owner).setMintActive(true);
    expect(await caller.tryMint.staticCall(await contract.getAddress(), { value: TIER1 })).to.equal(false);
    expect(await contract.totalSupply()).to.equal(0);
  });

  it("boundary: after 500 mints currentPrice is 0.0008 BNB and #501 costs tier 2", async function () {
    this.timeout(180000);
    const { contract, mock, owner } = await deployFixture();
    await contract.connect(owner).setMintActive(true);
    const wallets = Array.from({ length: 501 }, () => ethers.Wallet.createRandom().connect(ethers.provider));
    // Fund without transactions (Hardhat-only cheat for the test).
    for (const w of wallets) {
      await network.provider.send("hardhat_setBalance", [w.address, "0xB1A2BC2EC50000"]); // 0.05 ETH
    }
    // One Agent ID per wallet, in a single transaction.
    await mock.mintBatch(wallets.map((w) => w.address));
    for (let i = 0; i < 500; i++) {
      await contract.connect(wallets[i]).mint({ value: TIER1 });
    }
    expect(await contract.totalSupply()).to.equal(500);
    expect(await contract.nextTokenId()).to.equal(501);
    expect(await contract.ownerOf(500)).to.equal(wallets[499].address);
    expect(await contract.currentPrice()).to.equal(TIER2);
    // Token #501 mints at the tier-2 price.
    await expect(contract.connect(wallets[500]).mint({ value: TIER2 }))
      .to.emit(contract, "Minted")
      .withArgs(wallets[500].address, 501, TIER2, anyValue);
    expect(await contract.totalSupply()).to.equal(501);
  });

  it("owner can change registry and disable the Agent ID check — then anyone can mint", async function () {
    const { contract, owner, alice } = await deployFixture();
    await contract.connect(owner).setMintActive(true);
    // No Agent ID: blocked while the check is on.
    await expect(contract.connect(alice).mint({ value: TIER1 })).to.be.revertedWithCustomError(
      contract,
      "NoAgentId"
    );
    await contract.connect(owner).setAgentIdCheckRequired(false);
    expect(await contract.agentIdCheckRequired()).to.equal(false);
    await contract.connect(alice).mint({ value: TIER1 });
    expect(await contract.ownerOf(1)).to.equal(alice.address);
    await expect(contract.connect(alice).setAgentIdCheckRequired(true)).to.be.revertedWithCustomError(
      contract,
      "OwnableUnauthorizedAccount"
    );
    await expect(
      contract.connect(owner).setAgentIdRegistry(ethers.ZeroAddress)
    ).to.be.revertedWithCustomError(contract, "InvalidAddress");
  });

  it("with the real SPACE ID registry on a local chain, mint reverts NoAgentId", async function () {
    const [owner, revenue] = await ethers.getSigners();
    const Factory = await ethers.getContractFactory("XovrathNFT");
    const contract = await Factory.deploy(owner.address, revenue.address, REAL_REGISTRY, "");
    await contract.waitForDeployment();
    expect(await contract.agentIdRegistry()).to.equal(REAL_REGISTRY);
    await contract.connect(owner).setMintActive(true);
    // No code at the real registry address on the local chain,
    // so hasAgentId is false and mint is blocked — exactly the
    // on-chain behaviour for a wallet without an Agent ID.
    expect(await contract.hasAgentId(owner.address)).to.equal(false);
    await expect(contract.connect(owner).mint({ value: TIER1 })).to.be.revertedWithCustomError(
      contract,
      "NoAgentId"
    );
  });

  it("tier prices changeable only before the first mint; boundary 500 never moves", async function () {
    const { contract, mock, owner, alice } = await deployFixture();
    await contract.connect(owner).setTierPrices(ethers.parseEther("0.0003"), ethers.parseEther("0.0009"));
    expect(await contract.priceTier1()).to.equal(ethers.parseEther("0.0003"));
    expect(await contract.TIER_1_END()).to.equal(500);
    await contract.connect(owner).setTierPrices(TIER1, TIER2);
    await giveAgentId(mock, alice);
    await contract.connect(owner).setMintActive(true);
    await contract.connect(alice).mint({ value: TIER1 });
    await expect(
      contract.connect(owner).setTierPrices(TIER1, TIER2)
    ).to.be.revertedWithCustomError(contract, "PricesLocked");
  });

  it("withdraw sends the full balance only to revenue, only by owner", async function () {
    const { contract, mock, owner, revenue, alice, bob } = await deployFixture();
    await giveAgentId(mock, alice);
    await giveAgentId(mock, bob);
    await contract.connect(owner).setMintActive(true);
    await contract.connect(alice).mint({ value: TIER1 });
    await contract.connect(bob).mint({ value: TIER1 });
    const addr = await contract.getAddress();
    expect(await ethers.provider.getBalance(addr)).to.equal(TIER1 * 2n);
    await expect(contract.connect(alice).withdraw()).to.be.revertedWithCustomError(
      contract,
      "OwnableUnauthorizedAccount"
    );
    const before = await ethers.provider.getBalance(revenue.address);
    await contract.connect(owner).withdraw();
    expect(await ethers.provider.getBalance(addr)).to.equal(0);
    expect(await ethers.provider.getBalance(revenue.address)).to.equal(before + TIER1 * 2n);
    await expect(contract.connect(owner).withdraw()).to.be.revertedWithCustomError(contract, "NoFunds");
  });

  it("tokenURI reverts for a nonexistent token", async function () {
    const { contract } = await deployFixture();
    await expect(contract.tokenURI(1)).to.be.revertedWithCustomError(contract, "ERC721NonexistentToken");
  });
});
