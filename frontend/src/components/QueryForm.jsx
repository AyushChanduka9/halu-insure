function QueryForm({ question, setQuestion, onSubmit, loading }) {
  return (
    <form
      onSubmit={onSubmit}
      className="rounded-2xl border border-slate-800 bg-slate-900/80 p-5 shadow-lg shadow-black/30"
    >
      <label
        htmlFor="question"
        className="mb-2 block text-sm font-medium text-slate-300"
      >
        Ask your insurance question
      </label>

      <textarea
        id="question"
        rows={4}
        value={question}
        onChange={(event) => setQuestion(event.target.value)}
        placeholder="Example: Is rainwater harvesting covered in my policy?"
        className="w-full resize-none rounded-xl border border-slate-700 bg-slate-950 px-4 py-3 text-slate-100 outline-none ring-brand-500 transition focus:ring-2"
      />

      <button
        type="submit"
        disabled={loading}
        className="mt-4 inline-flex items-center justify-center rounded-xl bg-brand-500 px-5 py-2.5 text-sm font-semibold text-white transition hover:bg-brand-600 disabled:cursor-not-allowed disabled:opacity-70"
      >
        {loading ? "Checking..." : "Check with Halu-Insure"}
      </button>
    </form>
  );
}

export default QueryForm;
