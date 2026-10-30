const { expect } = require("chai");
const { ethers } = require("hardhat");

const TIER1 = ethers.parseEther("0.0002");
const TIER2 = ethers.parseEther("0.0008");

async function deployFixture() {
  const [owner, revenue, agent, alice, bob] = await ethers.getSigners();
  const Factory = await ethers.getContractFactory("XovrathNFT");
  const contract = await Factory.deploy(
    owner.address,
    revenue.address,
    agent.address,
    "ipfs://bafyTESTmetadata/"
  );
  await contract.waitForDeployment();
  return { contract, owner, revenue, agent, alice, bob };
}

// Sign an agent authorization for `minter` to mint `quantity`.
// Uses the contract's current nonce and a 1-hour deadline.
async function signMint(contract, agent, minter, quantity) {
  const nonce = await contract.nonces(minter.address);
  const deadline = (await ethers.provider.getBlock("latest")).timestamp + 3600;
  const domain = {
    name: "XOVRATH",
    version: "1",
    chainId: (await ethers.provider.getNetwork()).chainId,
    verifyingContract: await contract.getAddress(),
  };
  const types = {
    MintAuthorization: [
      { name: "minter", type: "address" },
      { name: "quantity", type: "uint256" },
      { name: "nonce", type: "uint256" },
      { name: "deadline", type: "uint256" },
    ],
  };
  const signature = await agent.signTypedData(domain, types, {
    minter: minter.address,
    quantity,
    nonce,
    deadline,
  });
  return { signature, deadline };
}

async function agentMint(contract, agent, minter, quantity) {
  const { signature, deadline } = await signMint(contract, agent, minter, quantity);
  const price = await contract.quoteMint(quantity);
  return contract.connect(minter).mint(quantity, deadline, signature, { value: price });
}

describe("XovrathNFT", function () {
  it("has the right name, symbol, supply, tiers and defaults", async function () {
    const { contract, owner, revenue, agent } = await deployFixture();
    expect(await contract.name()).to.equal("XOVRATH");
    expect(await contract.symbol()).to.equal("XOVR");
    expect(await contract.MAX_SUPPLY()).to.equal(2222);
    expect(await contract.TIER_1_END()).to.equal(500);
    expect(await contract.priceTier1()).to.equal(TIER1);
    expect(await contract.priceTier2()).to.equal(TIER2);
    expect(await contract.priceForTokenId(1)).to.equal(TIER1);
    expect(await contract.priceForTokenId(500)).to.equal(TIER1);
    expect(await contract.priceForTokenId(501)).to.equal(TIER2);
    expect(await contract.priceForTokenId(2222)).to.equal(TIER2);
    expect(await contract.mintActive()).to.equal(false);
    expect(await contract.agentAuthRequired()).to.equal(true);
    expect(await contract.owner()).to.equal(owner.address);
    expect(await contract.revenueWallet()).to.equal(revenue.address);
    expect(await contract.agentSigner()).to.equal(agent.address);
    expect(await contract.totalSupply()).to.equal(0);
    expect(await contract.nextTokenId()).to.equal(1);
    await expect(contract.quoteMint(0)).to.be.revertedWithCustomError(contract, "InvalidQuantity");
    await expect(contract.quoteMint(2223)).to.be.revertedWithCustomError(contract, "ExceedsMaxSupply");
  });

  it("refuses mint while inactive", async function () {
    const { contract, agent, alice } = await deployFixture();
    const { signature, deadline } = await signMint(contract, agent, alice, 1);
    await expect(
      contract.connect(alice).mint(1, deadline, signature, { value: TIER1 })
    ).to.be.revertedWithCustomError(contract, "MintInactive");
  });

  it("mints token #1 with the exact tier-1 price, agent signature, and tokenURI", async function () {
    const { contract, owner, agent, alice } = await deployFixture();
    await contract.connect(owner).setMintActive(true);
    await expect(agentMint(contract, agent, alice, 1))
      .to.emit(contract, "Minted")
      .withArgs(alice.address, 1, TIER1);
    expect(await contract.ownerOf(1)).to.equal(alice.address);
    expect(await contract.tokenURI(1)).to.equal("ipfs://bafyTESTmetadata/1.json");
    expect(await contract.totalSupply()).to.equal(1);
    expect(await contract.nextTokenId()).to.equal(2);
    expect(await contract.nonces(alice.address)).to.equal(1);
    expect(await contract.getMintPrice()).to.equal(TIER1);
  });

  it("rejects mint without agent signature, with wrong signer, expired, or replayed", async function () {
    const { contract, owner, agent, alice, bob } = await deployFixture();
    await contract.connect(owner).setMintActive(true);

    // No signature at all.
    await expect(
      contract.connect(alice).mint(1, 9999999999, "0x", { value: TIER1 })
    ).to.be.revertedWithCustomError(contract, "InvalidAgentSignature");

    // Signed by the wrong account (bob is not the agent).
    const bad = await signMint(contract, bob, alice, 1);
    await expect(
      contract.connect(alice).mint(1, bad.deadline, bad.signature, { value: TIER1 })
    ).to.be.revertedWithCustomError(contract, "InvalidAgentSignature");

    // Expired deadline.
    const nonce = await contract.nonces(alice.address);
    const domain = {
      name: "XOVRATH",
      version: "1",
      chainId: (await ethers.provider.getNetwork()).chainId,
      verifyingContract: await contract.getAddress(),
    };
    const types = {
      MintAuthorization: [
        { name: "minter", type: "address" },
        { name: "quantity", type: "uint256" },
        { name: "nonce", type: "uint256" },
        { name: "deadline", type: "uint256" },
      ],
    };
    const expiredSig = await agent.signTypedData(domain, types, {
      minter: alice.address,
      quantity: 1,
      nonce,
      deadline: 1,
    });
    await expect(
      contract.connect(alice).mint(1, 1, expiredSig, { value: TIER1 })
    ).to.be.revertedWithCustomError(contract, "AuthorizationExpired");

    // Valid signature works once, then replaying it fails (nonce moved).
    const good = await signMint(contract, agent, alice, 1);
    await contract.connect(alice).mint(1, good.deadline, good.signature, { value: TIER1 });
    await expect(
      contract.connect(alice).mint(1, good.deadline, good.signature, { value: TIER1 })
    ).to.be.revertedWithCustomError(contract, "InvalidAgentSignature");
  });

  it("rejects underpayment and overpayment, and enforces exact payment", async function () {
    const { contract, owner, agent, alice } = await deployFixture();
    await contract.connect(owner).setMintActive(true);
    const low = await signMint(contract, agent, alice, 1);
    await expect(
      contract.connect(alice).mint(1, low.deadline, low.signature, { value: TIER1 - 1n })
    ).to.be.revertedWithCustomError(contract, "IncorrectPayment");
    const high = await signMint(contract, agent, alice, 1);
    await expect(
      contract.connect(alice).mint(1, high.deadline, high.signature, { value: TIER1 + 1n })
    ).to.be.revertedWithCustomError(contract, "IncorrectPayment");
  });

  it("boundary: 499 minted + mint(3) costs 0.0018 BNB for #500, #501, #502", async function () {
    const { contract, owner, agent, alice } = await deployFixture();
    await contract.connect(owner).setMintActive(true);
    // Mint 499 in batches: 100 + 100 + 100 + 100 + 99.
    for (const qty of [100, 100, 100, 100, 99]) {
      await agentMint(contract, agent, alice, qty);
    }
    expect(await contract.totalSupply()).to.equal(499);
    expect(await contract.nextTokenId()).to.equal(500);

    const detailed = await contract.quoteMintDetailed(3);
    expect(detailed[0]).to.deep.equal([500n, 501n, 502n]);
    expect(detailed[1]).to.deep.equal([TIER1, TIER2, TIER2]);
    expect(detailed[2]).to.equal(ethers.parseEther("0.0018"));
    expect(await contract.quoteMint(3)).to.equal(ethers.parseEther("0.0018"));

    await expect(agentMint(contract, agent, alice, 3))
      .to.emit(contract, "Minted")
      .withArgs(alice.address, 500, TIER1);
    expect(await contract.ownerOf(500)).to.equal(alice.address);
    expect(await contract.ownerOf(501)).to.equal(alice.address);
    expect(await contract.ownerOf(502)).to.equal(alice.address);
    expect(await contract.totalSupply()).to.equal(502);
    expect(await contract.getMintPrice()).to.equal(TIER2);
  });

  it("owner can change agent signer and disable agent auth — then mint needs no signature", async function () {
    const { contract, owner, agent, alice, bob } = await deployFixture();
    await contract.connect(owner).setMintActive(true);
    await contract.connect(owner).setAgentSigner(bob.address);
    expect(await contract.agentSigner()).to.equal(bob.address);
    // Old agent's signature no longer works.
    const stale = await signMint(contract, agent, alice, 1);
    await expect(
      contract.connect(alice).mint(1, stale.deadline, stale.signature, { value: TIER1 })
    ).to.be.revertedWithCustomError(contract, "InvalidAgentSignature");
    // Disable enforcement: mint with an empty signature works.
    await contract.connect(owner).setAgentAuthRequired(false);
    await contract.connect(alice).mint(1, 0, "0x", { value: TIER1 });
    expect(await contract.ownerOf(1)).to.equal(alice.address);
    // Non-owner cannot touch admin functions.
    await expect(contract.connect(alice).setAgentAuthRequired(true)).to.be.revertedWithCustomError(
      contract,
      "OwnableUnauthorizedAccount"
    );
  });

  it("tier prices changeable only before the first mint; boundary 500 never moves", async function () {
    const { contract, owner, agent, alice } = await deployFixture();
    await contract.connect(owner).setTierPrices(ethers.parseEther("0.0003"), ethers.parseEther("0.0009"));
    expect(await contract.priceTier1()).to.equal(ethers.parseEther("0.0003"));
    expect(await contract.priceTier2()).to.equal(ethers.parseEther("0.0009"));
    expect(await contract.TIER_1_END()).to.equal(500);
    // Restore spec prices, activate, mint once — then prices lock.
    await contract.connect(owner).setTierPrices(TIER1, TIER2);
    await contract.connect(owner).setMintActive(true);
    await agentMint(contract, agent, alice, 1);
    await expect(
      contract.connect(owner).setTierPrices(TIER1, TIER2)
    ).to.be.revertedWithCustomError(contract, "PricesLocked");
  });

  it("withdraw sends the full balance only to revenue, only by owner", async function () {
    const { contract, owner, revenue, agent, alice } = await deployFixture();
    await contract.connect(owner).setMintActive(true);
    await agentMint(contract, agent, alice, 2);
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
    await expect(contract.priceForTokenId(0)).to.be.revertedWithCustomError(contract, "ExceedsMaxSupply");
    await expect(contract.priceForTokenId(2223)).to.be.revertedWithCustomError(contract, "ExceedsMaxSupply");
  });
});
