import TrustScore from "./TrustScore";

function ResultCard({ result }) {
  const verdictLabel = result.is_hallucination ? "Hallucination" : "Looks grounded";
  const verdictStyles = result.is_hallucination
    ? "border-rose-500/40 bg-rose-500/10 text-rose-300"
    : "border-emerald-500/40 bg-emerald-500/10 text-emerald-300";

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
            <p className="mt-1 text-lg font-semibold text-brand-400">
              {(result.confidence * 100).toFixed(1)}%
            </p>
          </div>
          <div className={`rounded-xl border p-4 ${verdictStyles}`}>
            <p className="text-xs uppercase tracking-wide">Hallucination Verdict</p>
            <p className="mt-1 text-lg font-semibold">{verdictLabel}</p>
          </div>
        </div>

        <div>
          <p className="text-xs uppercase tracking-wide text-slate-400">Evidence</p>
          <p className="mt-1 text-slate-200">{result.evidence}</p>
        </div>

        <div className="grid gap-3 sm:grid-cols-2">
          <div className="rounded-xl border border-slate-800 bg-slate-950/60 p-4">
            <p className="text-xs uppercase tracking-wide text-slate-400">Stake Amount</p>
            <p className="mt-1 text-slate-100">{result.stake_amount}</p>
          </div>
          <div className="rounded-xl border border-slate-800 bg-slate-950/60 p-4">
            <p className="text-xs uppercase tracking-wide text-slate-400">Transaction Hash</p>
            <p className="mt-1 break-all text-sm text-slate-200">{result.tx_hash}</p>
          </div>
        </div>

        <TrustScore score={result.trust_score} />
      </div>
    </div>
  );
}

export default ResultCard;
