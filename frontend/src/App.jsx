import { useEffect, useState } from "react";
import { ethers } from "ethers";
import QueryForm from "./components/QueryForm";
import ResultCard from "./components/ResultCard";

const SEPOLIA_CHAIN_ID = 11155111n;

function shortenAddress(address) {
  if (!address) return "";
  return `${address.slice(0, 6)}...${address.slice(-4)}`;
}

function getNetworkLabel(network) {
  if (!network) return "Not connected";
  if (network.chainId === SEPOLIA_CHAIN_ID) return "Sepolia";
  if (network.name && network.name !== "unknown") return network.name;
  return `Chain ID ${network.chainId.toString()}`;
}

function LoadingSpinner() {
  const loadingSteps = [
    "Generating AI response...",
    "Auditing with RAG...",
    "Submitting blockchain transaction...",
  ];
  const [activeStep, setActiveStep] = useState(0);

  useEffect(() => {
    const interval = window.setInterval(() => {
      setActiveStep((previousStep) => (previousStep + 1) % loadingSteps.length);
    }, 1400);

    return () => window.clearInterval(interval);
  }, [loadingSteps.length]);

  return (
    <div className="rounded-2xl border border-slate-800 bg-slate-900/80 p-6 shadow-lg shadow-black/30">
      <div className="flex items-center gap-3">
        <div className="h-3 w-3 animate-pulse rounded-full bg-amber-400 shadow-[0_0_18px_rgba(251,191,36,0.9)]" />
        <p className="text-sm font-medium text-slate-200">Processing your query</p>
      </div>

      <div className="mt-4 rounded-xl border border-slate-800 bg-slate-950/60 p-4">
        <div className="h-3 w-full animate-pulse rounded bg-slate-800" />
        <div className="mt-3 h-3 w-2/3 animate-pulse rounded bg-slate-800" />
      </div>

      <div className="mt-4 space-y-2">
        {loadingSteps.map((step, index) => {
          const isActive = activeStep === index;
          const isCompleted = activeStep > index;

          return (
            <div
              key={step}
              className={`flex items-center gap-2 rounded-lg px-3 py-2 text-sm transition ${
                isActive
                  ? "bg-blue-500/10 text-blue-200 shadow-[0_0_18px_rgba(59,130,246,0.45)]"
                  : "text-slate-400"
              }`}
            >
              <span
                className={`inline-block h-2.5 w-2.5 rounded-full ${
                  isCompleted
                    ? "bg-emerald-400"
                    : isActive
                    ? "bg-blue-400 animate-pulse"
                    : "bg-slate-600"
                }`}
              />
              <span>{step}</span>
            </div>
          );
        })}
      </div>
    </div>
  );
}

function App() {
  const [question, setQuestion] = useState("");
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [walletAddress, setWalletAddress] = useState("");
  const [network, setNetwork] = useState(null);
  const [walletError, setWalletError] = useState("");
  const [connectingWallet, setConnectingWallet] = useState(false);

  const isMetaMaskInstalled =
    typeof window !== "undefined" && typeof window.ethereum !== "undefined";
  const isWrongNetwork = walletAddress && network?.chainId !== SEPOLIA_CHAIN_ID;

  const syncWalletState = async () => {
    if (!isMetaMaskInstalled) return;

    const provider = new ethers.BrowserProvider(window.ethereum);
    const accounts = await provider.send("eth_accounts", []);
    const currentNetwork = await provider.getNetwork();

    setNetwork(currentNetwork);
    setWalletAddress(accounts[0] || "");
  };

  const handleSubmit = async (event) => {
    event.preventDefault();
    const trimmedQuestion = question.trim();

    if (!trimmedQuestion) {
      setError("Please enter a question first.");
      return;
    }

    setError("");
    setLoading(true);
    setResult(null);

    try {
      const response = await fetch("http://127.0.0.1:8000/query", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ question: trimmedQuestion }),
      });

      if (!response.ok) {
        throw new Error(`Request failed with status ${response.status}`);
      }

      const data = await response.json();
      setResult(data);
    } catch (requestError) {
      setError(
        requestError?.message ||
          "Could not reach backend. Is FastAPI running on port 8000?"
      );
    } finally {
      setLoading(false);
    }
  };

  const handleConnectWallet = async () => {
    if (!isMetaMaskInstalled) {
      setWalletError("MetaMask is not installed. Please install it and try again.");
      return;
    }

    setWalletError("");
    setConnectingWallet(true);

    try {
      const provider = new ethers.BrowserProvider(window.ethereum);
      await provider.send("eth_requestAccounts", []);
      await syncWalletState();
    } catch (connectError) {
      setWalletError(
        connectError?.info?.error?.message ||
          connectError?.shortMessage ||
          connectError?.message ||
          "Could not connect wallet. Please try again."
      );
    } finally {
      setConnectingWallet(false);
    }
  };

  useEffect(() => {
    if (!isMetaMaskInstalled) return;

    syncWalletState().catch(() => {
      setWalletError("Could not read wallet status from MetaMask.");
    });

    const handleAccountsChanged = (accounts) => {
      setWalletAddress(accounts[0] || "");
      setWalletError("");
      syncWalletState().catch(() => {
        setWalletError("Could not refresh wallet after account change.");
      });
    };

    const handleChainChanged = () => {
      setWalletError("");
      syncWalletState().catch(() => {
        setWalletError("Could not refresh wallet after network change.");
      });
    };

    window.ethereum.on("accountsChanged", handleAccountsChanged);
    window.ethereum.on("chainChanged", handleChainChanged);

    return () => {
      window.ethereum.removeListener("accountsChanged", handleAccountsChanged);
      window.ethereum.removeListener("chainChanged", handleChainChanged);
    };
  }, [isMetaMaskInstalled]);

  return (
    <main className="min-h-screen bg-gradient-to-b from-slate-950 to-slate-900 px-4 py-10 text-slate-100">
      <div className="mx-auto w-full max-w-3xl space-y-6">
        <header className="text-center">
          <p className="text-sm uppercase tracking-[0.25em] text-brand-400">
            Halu-Insure
          </p>
          <h1 className="mt-2 text-3xl font-bold sm:text-4xl">
            AI Answer Insurance
          </h1>
          <p className="mt-2 text-slate-400">
            Ask a question and verify answer quality with prover + auditor + blockchain.
          </p>
        </header>

        <section className="rounded-2xl border border-slate-800 bg-slate-900/80 p-5 shadow-lg shadow-black/30">
          <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
            <div>
              <p className="text-sm text-slate-300">Wallet</p>
              <p className="text-sm text-slate-400">
                {walletAddress
                  ? `Connected: ${shortenAddress(walletAddress)}`
                  : "No wallet connected"}
              </p>
              <p className="text-sm text-slate-400">
                Network: {getNetworkLabel(network)}
              </p>
            </div>

            <button
              type="button"
              onClick={handleConnectWallet}
              disabled={connectingWallet}
              className="rounded-lg bg-brand-500 px-4 py-2 text-sm font-semibold text-white transition hover:bg-brand-600 disabled:cursor-not-allowed disabled:opacity-60"
            >
              {connectingWallet ? "Connecting..." : "Connect Wallet"}
            </button>
          </div>

          {!isMetaMaskInstalled && (
            <p className="mt-3 rounded-lg border border-amber-500/40 bg-amber-500/10 px-3 py-2 text-sm text-amber-200">
              MetaMask not detected. Install MetaMask to connect your wallet.
            </p>
          )}

          {walletError && (
            <p className="mt-3 rounded-lg border border-rose-500/40 bg-rose-500/10 px-3 py-2 text-sm text-rose-200">
              {walletError}
            </p>
          )}

          {isWrongNetwork && (
            <p className="mt-3 rounded-lg border border-amber-500/40 bg-amber-500/10 px-3 py-2 text-sm text-amber-200">
              Wrong network. Please switch MetaMask to Sepolia.
            </p>
          )}
        </section>

        <QueryForm
          question={question}
          setQuestion={setQuestion}
          onSubmit={handleSubmit}
          loading={loading}
        />

        {error && (
          <div className="rounded-xl border border-rose-500/40 bg-rose-500/10 px-4 py-3 text-sm text-rose-200">
            {error}
          </div>
        )}

        {loading && <LoadingSpinner />}
        {result && <ResultCard result={result} />}
      </div>
    </main>
  );
}

export default App;
