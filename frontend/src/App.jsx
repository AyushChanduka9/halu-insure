import { useState } from "react";
import QueryForm from "./components/QueryForm";
import ResultCard from "./components/ResultCard";

function LoadingSpinner() {
  return (
    <div className="rounded-2xl border border-slate-800 bg-slate-900/80 p-8 text-center shadow-lg shadow-black/30">
      <div className="mx-auto h-10 w-10 animate-spin rounded-full border-4 border-slate-700 border-t-brand-500" />
      <p className="mt-3 text-sm text-slate-300">Checking with prover + auditor...</p>
    </div>
  );
}

function App() {
  const [question, setQuestion] = useState("");
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

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
