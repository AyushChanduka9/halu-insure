/**
 * Halu Insure — Hardhat configuration (beginner-friendly defaults).
 *
 * For Sepolia deployment:
 *   - Copy `.env.example` to `.env` in this same folder (project root).
 *   - Set SEPOLIA_RPC_URL and PRIVATE_KEY (see `.env.example`).
 *
 * `dotenv` loads `.env` from the current working directory when you run Hardhat
 * (run commands from the repo root so the root `.env` is picked up).
 */

require("dotenv").config();
require("@nomicfoundation/hardhat-toolbox");

/**
 * Hardhat expects private keys as hex strings, with or without the 0x prefix.
 * @returns {string[]} list with one normalized key, or [] if PRIVATE_KEY is unset
 */
function accountsFromEnv() {
  const raw = process.env.PRIVATE_KEY;
  if (raw === undefined || String(raw).trim() === "") {
    return [];
  }
  const k = String(raw).trim();
  return [k.startsWith("0x") || k.startsWith("0X") ? k : `0x${k}`];
}

/** @type import("hardhat/config").HardhatUserConfig */
module.exports = {
  solidity: {
    version: "0.8.20",
    settings: {
      optimizer: {
        enabled: true,
        runs: 200,
      },
    },
  },
  paths: {
    sources: "./contracts",
    tests: "./test",
    cache: "./cache",
    artifacts: "./artifacts",
  },
  networks: {
    // Local deterministic chain — no `.env` required.
    hardhat: {},
    // Ethereum Sepolia testnet (chain id 11155111).
    sepolia: {
      url: process.env.SEPOLIA_RPC_URL || "",
      accounts: accountsFromEnv(),
      chainId: 11155111,
    },
  },
};
