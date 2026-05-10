/**
 * Deploy `HaluInsure` to Ethereum Sepolia.
 *
 * Loads settings from the project root `.env` file (see `hardhat.config.js`):
 *   - SEPOLIA_RPC_URL — HTTPS endpoint to a Sepolia node
 *   - PRIVATE_KEY — deployer wallet (must hold Sepolia ETH for gas)
 *
 * Run from the repository root (same folder as `package.json`):
 *   npx hardhat run scripts/deploy.js --network sepolia
 *
 * Never commit your real `.env` or share your private key.
 */

const hre = require("hardhat");

async function main() {
  const rpc = process.env.SEPOLIA_RPC_URL?.trim();
  const pk = process.env.PRIVATE_KEY?.trim();

  if (!rpc) {
    console.error(
      "Error: SEPOLIA_RPC_URL is missing.\n" +
        "Create a file named `.env` in the project root (next to package.json) and add:\n" +
        "  SEPOLIA_RPC_URL=https://...\n"
    );
    process.exit(1);
  }

  if (!pk) {
    console.error(
      "Error: PRIVATE_KEY is missing.\n" +
        "Add to your project root `.env`:\n" +
        "  PRIVATE_KEY=0x...   (64 hex characters after 0x)\n"
    );
    process.exit(1);
  }

  const signers = await hre.ethers.getSigners();
  const deployer = signers[0];
  if (!deployer) {
    console.error(
      "Error: Hardhat has no signing account. Check PRIVATE_KEY in `.env` and that you used `--network sepolia`."
    );
    process.exit(1);
  }

  console.log("Deploying with account:", deployer.address);

  const HaluInsure = await hre.ethers.getContractFactory("HaluInsure");
  const contract = await HaluInsure.deploy();
  await contract.waitForDeployment();

  const address = await contract.getAddress();

  console.log("");
  console.log("Success — HaluInsure is on Sepolia at:");
  console.log(address);
  console.log("");
  console.log("Next step: copy this line into backend/.env (for the Python backend):");
  console.log(`HALU_CONTRACT_ADDRESS=${address}`);
  console.log("");
  console.log("Use the same SEPOLIA_RPC_URL in backend/.env if the API should talk to the same network,");
  console.log("and set BACKEND_PRIVATE_KEY when the backend wallet should submit transactions.");
}

main().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});
