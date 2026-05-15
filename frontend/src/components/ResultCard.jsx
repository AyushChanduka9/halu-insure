import { useEffect, useMemo, useState } from "react";
import TrustScore from "./TrustScore";

function ResultCard({ result }) {
  const verdictLabel = result.is_hallucination ? "Hallucination" : "Looks grounded";
  const verdictStyles = result.is_hallucination
    ? "border-rose-500/40 bg-rose-500/10 text-rose-300 shadow-[0_0_22px_rgba(244,63,94,0.45)]"
    : "border-emerald-500/40 bg-emerald-500/10 text-emerald-300 shadow-[0_0_22px_rgba(16,185,129,0.45)]";
  const retrievedChunks = Array.isArray(result.retrieved_chunks)
    ? result.retrieved_chunks.slice(0, 3)
    : [];
  const safeConfidence = Math.max(0, Math.min(result.confidence ?? 0, 1));
  const [animatedConfidence, setAnimatedConfidence] = useState(0);

  const confidenceTheme = useMemo(() => {
    if (safeConfidence >= 0.75) {
      return {
        label: "High",
        textClass: "text-emerald-300",
        barClass: "from-emerald-500 to-green-400",
        glowClass: "shadow-[0_0_24px_rgba(34,197,94,0.45)]",
      };
    }

    if (safeConfidence >= 0.45) {
      return {
        label: "Medium",
        textClass: "text-amber-300",
        barClass: "from-amber-500 to-yellow-400",
        glowClass: "shadow-[0_0_24px_rgba(250,204,21,0.45)]",
      };
    }

    return {
      label: "Low",
      textClass: "text-rose-300",
      barClass: "from-rose-500 to-red-400",
      glowClass: "shadow-[0_0_24px_rgba(248,113,113,0.45)]",
    };
  }, [safeConfidence]);

  useEffect(() => {
    const timer = window.setTimeout(() => {
      setAnimatedConfidence(safeConfidence * 100);
    }, 80);

    return () => window.clearTimeout(timer);
  }, [safeConfidence]);

  return (
    <div className="rounded-2xl border border-slate-800 bg-slate-900/80 p-5 shadow-lg shadow-black/30">
      <h2 className="text-lg font-semibold text-slate-100">Result</h2>

      <div className="mt-4 space-y-4">
        <div>
          <p className="text-xs uppercase tracking-wide text-slate-400">Answer</p>
          <p className="mt-1 text-slate-100">{result.answer}</p>
        </div>

        <div className="grid gap-3 sm:grid-cols-2">
          <div className="rounded-xl border border-slate-800 bg-slate-950/60 p-4">
            <p className="text-xs uppercase tracking-wide text-slate-400">
              Confidence
            </p>
            <div className="mt-1 flex items-center justify-between">
              <p className={`text-lg font-semibold ${confidenceTheme.textClass}`}>
                {(safeConfidence * 100).toFixed(1)}%
              </p>
              <span
                className={`rounded-full border px-2 py-0.5 text-xs font-medium ${confidenceTheme.textClass} ${confidenceTheme.glowClass}`}
              >
                {confidenceTheme.label}
              </span>
            </div>
            <div className="mt-3 h-2.5 overflow-hidden rounded-full bg-slate-800">
              <div
                className={`h-full rounded-full bg-gradient-to-r transition-[width] duration-700 ease-out ${confidenceTheme.barClass}`}
                style={{ width: `${animatedConfidence}%` }}
              />
            </div>
            <p className="mt-2 text-xs text-slate-400">
              Confidence meter updates smoothly after result arrives.
            </p>
          </div>
          <div className={`rounded-xl border p-4 ${verdictStyles}`}>
            <div className="flex items-center justify-between">
              <p className="text-xs uppercase tracking-wide">Hallucination Verdict</p>
              <span
                className={`rounded-full border px-2 py-0.5 text-xs ${
                  result.is_hallucination
                    ? "border-rose-500/50 bg-rose-500/20 text-rose-200 shadow-[0_0_16px_rgba(244,63,94,0.55)]"
                    : "border-emerald-500/50 bg-emerald-500/20 text-emerald-200 shadow-[0_0_16px_rgba(16,185,129,0.55)]"
                }`}
              >
                {result.is_hallucination ? "Alert" : "Verified"}
              </span>
            </div>
            <p className="mt-1 text-lg font-semibold">{verdictLabel}</p>
          </div>
        </div>

        <div className="grid gap-3 sm:grid-cols-2">
          <div className="rounded-xl border border-slate-800 bg-slate-950/60 p-4">
            <p className="text-xs uppercase tracking-wide text-slate-400">Pipeline Status</p>
            <span className="mt-2 inline-flex items-center gap-2 rounded-full border border-blue-500/40 bg-blue-500/10 px-2.5 py-1 text-xs text-blue-200 shadow-[0_0_16px_rgba(59,130,246,0.5)]">
              <span className="h-2 w-2 animate-pulse rounded-full bg-blue-400" />
              Completed
            </span>
            <p className="mt-2 text-xs text-slate-400">
              Response, audit, and transaction steps are done.
            </p>
          </div>
          <div className="rounded-xl border border-slate-800 bg-slate-950/60 p-4">
            <p className="text-xs uppercase tracking-wide text-slate-400">Review Status</p>
            <span className="mt-2 inline-flex items-center gap-2 rounded-full border border-amber-500/40 bg-amber-500/10 px-2.5 py-1 text-xs text-amber-200 shadow-[0_0_16px_rgba(245,158,11,0.55)]">
              <span className="h-2 w-2 animate-pulse rounded-full bg-amber-400" />
              Ready to inspect
            </span>
            <p className="mt-2 text-xs text-slate-400">
              Use evidence and score to make the final trust decision.
            </p>
          </div>
        </div>

        <div>
          <p className="text-xs uppercase tracking-wide text-slate-400">Evidence</p>
          <p className="mt-1 text-slate-200">{result.evidence}</p>
        </div>

        <div>
          <p className="text-xs uppercase tracking-wide text-slate-400">
            Retrieved Evidence
          </p>
          {retrievedChunks.length > 0 ? (
            <div className="mt-2 space-y-2">
              {retrievedChunks.map((chunk, index) => (
                <div
                  key={`${index}-${chunk.slice(0, 30)}`}
                  className="rounded-xl border border-slate-800 bg-slate-950/70 p-3 text-sm text-slate-200"
                >
                  <p className="mb-1 text-xs uppercase tracking-wide text-slate-500">
                    Chunk {index + 1}
                  </p>
                  <p>{chunk}</p>
                </div>
              ))}
            </div>
          ) : (
            <p className="mt-1 text-sm text-slate-400">No retrieved chunks available.</p>
          )}
        </div>

        <div className="grid gap-3 sm:grid-cols-2">
          <div className="rounded-xl border border-slate-800 bg-slate-950/60 p-4">
            <p className="text-xs uppercase tracking-wide text-slate-400">Stake Amount</p>
            <p className="mt-1 text-slate-100">{result.stake_amount}</p>
          </div>
          <div className="rounded-xl border border-slate-800 bg-slate-950/60 p-4">
            <p className="text-xs uppercase tracking-wide text-slate-400">Transaction Hash</p>
            <a
              href={`https://sepolia.etherscan.io/tx/${result.tx_hash}`}
              target="_blank"
              rel="noopener noreferrer"
              className="mt-1 inline-block break-all text-sm text-blue-300 underline-offset-4 transition hover:text-blue-200 hover:underline hover:drop-shadow-[0_0_8px_rgba(59,130,246,0.8)]"
            >
              {result.tx_hash}
            </a>
          </div>
        </div>

        <TrustScore score={result.trust_score} />
      </div>
    </div>
  );
}

export default ResultCard;
