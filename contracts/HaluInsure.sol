// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import {Ownable} from "@openzeppelin/contracts/access/Ownable.sol";

/// @notice Minimal insurer-style stake + trust scaffolding for Halu claims.
contract HaluInsure is Ownable {
    /// @notice All-time stake weight per address (Ether locked via this contract).
    mapping(address => uint256) public stakes;

    /// @notice Packed trust scores: unset (0) means "display 100", otherwise stored == display + 1.
    mapping(address => uint256) private trustScore;

    /// @notice Claims keyed by a unique id (often a commitment / query hash).
    mapping(bytes32 => Claim) public claims;

    /// @dev Contract owner is managed by OpenZeppelin `Ownable` (see `owner()`).

    uint256 public constant NORMAL_STAKE = 0.001 ether;
    uint256 public constant HIGH_STAKE = 0.005 ether;

    uint256 public constant RELEASE_DELAY = 1 days;

    struct Claim {
        address prover;
        bytes32 queryHash;
        uint256 stakeAmount;
        bool resolved;
        bool slashed;
        uint256 timestamp;
    }

    event Staked(bytes32 indexed claimId, address indexed prover, uint256 amount);
    event Released(bytes32 indexed claimId, address indexed prover);
    event Slashed(bytes32 indexed claimId, address indexed prover, uint256 amount);
    event Disputed(bytes32 indexed claimId, address indexed disputer);

    constructor() Ownable(msg.sender) {}

    /// @notice Lock stake on a claim. First sender becomes the claim prover for this id.
    function stake(bytes32 claimId, bool highRisk) external payable {
        uint256 required = highRisk ? HIGH_STAKE : NORMAL_STAKE;
        require(msg.value == required, "HaluInsure: wrong stake amount");

        Claim storage c = claims[claimId];

        if (c.prover == address(0)) {
            require(claimId != bytes32(0), "HaluInsure: empty claim id");
            c.prover = msg.sender;
            c.queryHash = claimId;
            c.timestamp = block.timestamp;
        } else {
            require(msg.sender == c.prover, "HaluInsure: wrong prover");
            require(!c.resolved && !c.slashed, "HaluInsure: claim finalized");
            require(c.stakeAmount > 0, "HaluInsure: reclaim after zero stake");
            c.timestamp = block.timestamp;
        }

        c.stakeAmount += msg.value;
        stakes[msg.sender] += msg.value;

        emit Staked(claimId, msg.sender, msg.value);
    }

    /// @notice Successful path: withdraw stake plus trust bonus after cooldown.
    function release(bytes32 claimId) external {
        Claim storage c = claims[claimId];
        require(c.prover != address(0), "HaluInsure: unknown claim");
        require(msg.sender == c.prover, "HaluInsure: not prover");
        require(!c.slashed, "HaluInsure: slashed");
        require(!c.resolved, "HaluInsure: already finalized");
        require(block.timestamp >= c.timestamp + RELEASE_DELAY, "HaluInsure: too early");
        uint256 payout = c.stakeAmount;
        require(payout > 0, "HaluInsure: nothing staked");

        c.resolved = true;
        c.stakeAmount = 0;
        stakes[c.prover] -= payout;

        _applyTrustBonus(c.prover, 10);

        emit Released(claimId, c.prover);

        (bool ok, ) = payable(c.prover).call{value: payout}("");
        require(ok, "HaluInsure: payout failed");
    }

    /// @notice Owner slashes a fraudulent/incorrect claim: stake forfeited to treasury.
    function slash(bytes32 claimId) external onlyOwner {
        Claim storage c = claims[claimId];
        require(c.prover != address(0), "HaluInsure: unknown claim");
        require(!c.slashed, "HaluInsure: already slashed");
        uint256 seized = c.stakeAmount;
        require(seized > 0, "HaluInsure: nothing at stake");

        c.slashed = true;
        c.resolved = true;
        c.stakeAmount = 0;

        stakes[c.prover] -= seized;
        _applyTrustPenalty(c.prover, 20);

        emit Slashed(claimId, c.prover, seized);

        (bool ok, ) = payable(owner()).call{value: seized}("");
        require(ok, "HaluInsure: slash transfer failed");
    }

    /// @notice Signals disagreement; emits an event hook for off-chain or future rules.
    function dispute(bytes32 claimId) external {
        Claim storage c = claims[claimId];
        require(c.prover != address(0), "HaluInsure: unknown claim");
        emit Disputed(claimId, msg.sender);
    }

    /// @return Trust score (defaults to 100 if never written).
    function getTrustScore(address agent) external view returns (uint256) {
        return _displayTrust(agent);
    }

    /// @return Live stake balance tracked for `agent`.
    function getStake(address agent) external view returns (uint256) {
        return stakes[agent];
    }

    function _displayTrust(address agent) internal view returns (uint256) {
        uint256 packed = trustScore[agent];
        return packed == 0 ? 100 : packed - 1;
    }

    function _saveTrust(address agent, uint256 displayValue) internal {
        trustScore[agent] = displayValue + 1;
    }

    function _applyTrustBonus(address agent, uint256 bump) internal {
        _saveTrust(agent, _displayTrust(agent) + bump);
    }

    function _applyTrustPenalty(address agent, uint256 cut) internal {
        uint256 current = _displayTrust(agent);
        _saveTrust(agent, current > cut ? current - cut : 0);
    }

    receive() external payable {}
}
