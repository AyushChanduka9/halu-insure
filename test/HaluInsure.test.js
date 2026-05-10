/**
 * HaluInsure — beginner-friendly Hardhat tests
 *
 * We use Hardhat Toolbox’s Chai matchers + ethers, and `@nomicfoundation/hardhat-network-helpers`
 * to move blockchain time forward (needed because `release()` waits `RELEASE_DELAY`).
 */

const { expect } = require("chai");
const { ethers } = require("hardhat");
const { time } = require("@nomicfoundation/hardhat-network-helpers");

/**
 * What we verify (plain English):
 *
 * 1. Normal stake: sending exactly 0.001 ETH with `highRisk = false` should succeed and lock funds.
 * 2. High-risk stake: sending exactly 0.005 ETH with `highRisk = true` should succeed.
 * 3. Wrong amount: if the ETH sent does not equal the exact required stake, the call must revert.
 * 4. Release trust bump: baseline trust reads as 100; after waiting and `release()`, trust should be +10 (110).
 * 5. Slash trust cut: baseline trust reads as 100; after owner `slash()`, the prover trust should drop by 20 (80).
 * 6. Dispute emits an event: `dispute()` must emit `Disputed` with the claim id + the caller address.
 * 7. Release twice: once a claim is released it is finalized; calling `release()` again must revert.
 * 8. Slash twice: once a claim is slashed/finalized, calling `slash()` again must revert.
 */

describe("HaluInsure", function () {
  /** Helper: fresh claim id derived from text (deterministic bytes32 per string). */
  function claimLabel(label) {
    return ethers.id(label);
  }

  /** Move time past when `release()` is allowed (stakes `RELEASE_DELAY`). */
  async function advancePastReleaseDelay(haluInsure) {
    const delay = await haluInsure.RELEASE_DELAY();
    await time.increase(delay);
  }

  let owner;
  let prover;
  let outsider;

  let halu;

  beforeEach(async function () {
    [owner, prover, outsider] = await ethers.getSigners();

    const HaluInsureFactory = await ethers.getContractFactory("HaluInsure");
    halu = await HaluInsureFactory.deploy();
    await halu.waitForDeployment();
  });

  describe("stake()", function () {
    it("1) normal stake succeeds with exactly 0.001 ETH", async function () {
      const claimId = claimLabel("norm-1");
      const amt = await halu.NORMAL_STAKE();

      await expect(
        halu.connect(prover).stake(claimId, false, { value: amt })
      )
        .to.emit(halu, "Staked")
        .withArgs(claimId, prover.address, amt);

      const c = await halu.claims(claimId);
      expect(c.prover).to.equal(prover.address);
      expect(c.stakeAmount).to.equal(amt);
      expect(await halu.getStake(prover.address)).to.equal(amt);
    });

    it("2) high-risk stake succeeds with exactly 0.005 ETH", async function () {
      const claimId = claimLabel("high-1");
      const amt = await halu.HIGH_STAKE();

      await expect(
        halu.connect(prover).stake(claimId, true, { value: amt })
      ).to.emit(halu, "Staked");

      const c = await halu.claims(claimId);
      expect(c.stakeAmount).to.equal(amt);
      expect(await halu.getStake(prover.address)).to.equal(amt);
    });

    it("3) wrong ETH amount reverts", async function () {
      const claimId = claimLabel("bad-amt");

      await expect(
        halu.connect(prover).stake(claimId, false, {
          value: ethers.parseEther("0.002"), // wrong: expected 0.001 for normal
        })
      ).to.be.revertedWith("HaluInsure: wrong stake amount");
    });
  });

  describe("release() and trust", function () {
    it("4) release() increases displayed trust score by +10 vs baseline", async function () {
      const claimId = claimLabel("trust-release");

      // Before any writes, on-chain getter still reports the design default of 100.
      expect(await halu.getTrustScore(prover.address)).to.equal(100n);

      await halu.connect(prover).stake(claimId, false, {
        value: await halu.NORMAL_STAKE(),
      });

      await advancePastReleaseDelay(halu);

      await halu.connect(prover).release(claimId);

      expect(await halu.getTrustScore(prover.address)).to.equal(110n);
    });

    it("7) cannot release an already resolved claim", async function () {
      const claimId = claimLabel("double-release");

      await halu.connect(prover).stake(claimId, false, {
        value: await halu.NORMAL_STAKE(),
      });

      await advancePastReleaseDelay(halu);

      await halu.connect(prover).release(claimId);

      await expect(
        halu.connect(prover).release(claimId)
      ).to.be.revertedWith("HaluInsure: already finalized");
    });
  });

  describe("slash() and trust", function () {
    it("5) slash() decreases displayed trust score by 20 vs baseline", async function () {
      const claimId = claimLabel("trust-slash");

      expect(await halu.getTrustScore(prover.address)).to.equal(100n);

      await halu.connect(prover).stake(claimId, false, {
        value: await halu.NORMAL_STAKE(),
      });

      await halu.connect(owner).slash(claimId);

      expect(await halu.getTrustScore(prover.address)).to.equal(80n);
    });

    it("8) cannot slash an already finalized/slashed claim twice", async function () {
      const claimId = claimLabel("double-slash");

      await halu.connect(prover).stake(claimId, false, {
        value: await halu.NORMAL_STAKE(),
      });

      await halu.connect(owner).slash(claimId);

      await expect(
        halu.connect(owner).slash(claimId)
      ).to.be.revertedWith("HaluInsure: already slashed");
    });
  });

  describe("dispute()", function () {
    it("6) dispute() emits Disputed with the right claim id + disputer", async function () {
      const claimId = claimLabel("dispute-emit");

      await halu.connect(prover).stake(claimId, false, {
        value: await halu.NORMAL_STAKE(),
      });

      await expect(halu.connect(outsider).dispute(claimId))
        .to.emit(halu, "Disputed")
        .withArgs(claimId, outsider.address);
    });
  });
});
