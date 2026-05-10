function TrustScore({ score }) {
  const safeScore = Math.max(0, Math.min(score ?? 0, 200));
  const percentage = (safeScore / 200) * 100;

  return (
    <div className="rounded-xl border border-slate-800 bg-slate-950/60 p-4">
      <div className="flex items-end justify-between">
        <p className="text-sm text-slate-400">Trust Score</p>
        <p className="text-xl font-bold text-brand-400">{safeScore} / 200</p>
      </div>

      <div className="mt-3 h-2.5 overflow-hidden rounded-full bg-slate-800">
        <div
          className="h-full rounded-full bg-gradient-to-r from-brand-600 to-brand-400"
          style={{ width: `${percentage}%` }}
        />
      </div>
    </div>
  );
}

export default TrustScore;
