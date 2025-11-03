const availableModels = ['gemini-2.5-flash', 'gemini-1.5-pro', 'llama-3.1-70b', 'custom-federated'];
const availableGraphs = [
  { id: 'hearing', label: 'Patient Data KG' },
  { id: 'psychiatry', label: 'Drug & Composition KG' },
  { id: 'unified', label: 'Public Medical Knowledge KG' },
];

export default function FinetunePage() {
  return (
    <div className="mx-auto flex max-w-5xl flex-col gap-12 px-6 py-16 text-[#1C1C1C]">
      <section className="flex flex-col gap-4 text-justify">
        <h1 className="text-3xl font-semibold">Finetune Your Grape Agent</h1>
        <p className="text-base text-[#4B5563]">
          Prototype dashboard for tailoring the agent to your domain. Select the
          underlying model, align it with the right graphs, and define the
          ontological guardrails before rolling out to your clinicians.
        </p>
      </section>

      <section className="grid gap-6 md:grid-cols-2">
        <div className="rounded-2xl border border-[#E5E7EB] bg-white p-6 shadow-sm">
          <h2 className="text-lg font-semibold text-[#1C1C1C]">Model &amp; runtime</h2>
          <p className="mt-2 text-sm text-[#4B5563] text-justify">
            Pick the reasoning model and execution profile that best suits your
            latency and accuracy constraints.
          </p>
          <div className="mt-6 space-y-4">
            <label className="flex flex-col gap-2 text-sm">
              <span className="font-medium text-[#1C1C1C]">Reasoning model</span>
              <select className="rounded-lg border border-[#E5E7EB] px-3 py-2 text-sm text-[#1C1C1C] focus:border-[#E57373] focus:outline-none">
                {availableModels.map(model => (
                  <option key={model}>{model}</option>
                ))}
              </select>
            </label>
            <label className="flex flex-col gap-2 text-sm">
              <span className="font-medium text-[#1C1C1C]">Temperature</span>
              <input
                type="range"
                min="0"
                max="1"
                step="0.05"
                defaultValue="0.2"
                className="accent-[#E57373]"
              />
              <span className="text-xs text-[#6B7280]">Lower values keep responses deterministic.</span>
            </label>
          </div>
        </div>

        <div className="rounded-2xl border border-[#E5E7EB] bg-white p-6 shadow-sm">
          <h2 className="text-lg font-semibold text-[#1C1C1C]">Knowledge graph scope</h2>
          <p className="mt-2 text-sm text-[#4B5563] text-justify">
            Decide which repositories the agent should query by default when answering.
          </p>
          <div className="mt-6 space-y-3">
            {availableGraphs.map(graph => (
              <label key={graph.id} className="flex items-center justify-between rounded-lg border border-[#E5E7EB] px-3 py-2 text-sm">
                <span className="text-[#1C1C1C]">{graph.label}</span>
                <input type="checkbox" defaultChecked={graph.id === 'unified'} className="h-4 w-4 accent-[#E57373]" />
              </label>
            ))}
            <label className="flex items-center justify-between rounded-lg border border-dashed border-[#E5E7EB] px-3 py-2 text-sm text-[#6B7280]">
              <span>+ Add external SPARQL endpoint</span>
              <span className="text-xs font-medium text-[#E57373]">Coming soon</span>
            </label>
          </div>
        </div>

        <div className="rounded-2xl border border-[#E5E7EB] bg-white p-6 shadow-sm md:col-span-2">
          <h2 className="text-lg font-semibold text-[#1C1C1C]">Guidance &amp; guardrails</h2>
          <p className="mt-2 text-sm text-[#4B5563] text-justify">
            Capture the pragmatic rules your clinicians expect: tone, evidence format, escalation criteria, and forbidden behaviours.
          </p>
          <div className="mt-6 grid gap-6 md:grid-cols-2">
            <div className="space-y-3 text-sm">
              <label className="flex flex-col gap-2">
                <span className="font-medium text-[#1C1C1C]">Response tone &amp; style</span>
                <textarea
                  rows={3}
                  className="w-full rounded-lg border border-[#E5E7EB] px-3 py-2 text-sm text-[#1C1C1C] focus:border-[#E57373] focus:outline-none"
                  placeholder="e.g., Clinical, cite ontology labels, highlight confidences…"
                />
              </label>
              <label className="flex items-center justify-between rounded-lg border border-[#E5E7EB] px-3 py-2">
                <span className="text-sm text-[#1C1C1C]">Always include supporting triples</span>
                <input type="checkbox" defaultChecked className="h-4 w-4 accent-[#E57373]" />
              </label>
              <label className="flex items-center justify-between rounded-lg border border-[#E5E7EB] px-3 py-2">
                <span className="text-sm text-[#1C1C1C]">Escalate when confidence &lt; 0.6</span>
                <input type="checkbox" className="h-4 w-4 accent-[#E57373]" />
              </label>
            </div>
            <div className="space-y-3 text-sm">
              <label className="flex flex-col gap-2">
                <span className="font-medium text-[#1C1C1C]">Ontology rules / SHACL snippet</span>
                <textarea
                  rows={6}
                  className="w-full rounded-lg border border-[#E5E7EB] px-3 py-2 font-mono text-xs text-[#1C1C1C] focus:border-[#E57373] focus:outline-none"
                  placeholder="PREFIX ex: <http://example.org/>\nSHACL rule or SWRL implication goes here…"
                />
              </label>
            </div>
          </div>
        </div>

        <div className="rounded-2xl border border-[#E5E7EB] bg-white p-6 shadow-sm">
          <h2 className="text-lg font-semibold text-[#1C1C1C]">Smoke test</h2>
          <p className="mt-2 text-sm text-[#4B5563] text-justify">
            Run a quick validation on your favourite demo scenario before deploying the finetuned agent.
          </p>
          <div className="mt-4 space-y-3 text-sm">
            <select className="w-full rounded-lg border border-[#E5E7EB] px-3 py-2 text-sm text-[#1C1C1C] focus:border-[#E57373] focus:outline-none">
              <option>Scenario 1 – Neighbourhood exploration</option>
              <option>Scenario 2 – Multi-hop reasoning</option>
              <option>Scenario 3 – Verifier (Ontology Proof)</option>
              <option>Scenario 4 – Deep Reasoning (S1→S3)</option>
            </select>
            <textarea
              rows={2}
              className="w-full rounded-lg border border-[#E5E7EB] px-3 py-2 text-sm text-[#1C1C1C] focus:border-[#E57373] focus:outline-none"
              placeholder="Enter a representative clinical question to test…"
            />
            <button
              type="button"
              className="w-full rounded-lg bg-[#E57373] px-4 py-2 text-sm font-semibold text-white transition-colors hover:bg-[#D55555]"
            >
              Run simulated test
            </button>
          </div>
        </div>

        <div className="rounded-2xl border border-[#E5E7EB] bg-white p-6 shadow-sm">
          <h2 className="text-lg font-semibold text-[#1C1C1C]">Deployment checklist</h2>
          <ul className="mt-4 space-y-3 text-sm text-[#4B5563]">
            <li>• Model &amp; temperature configured</li>
            <li>• Graph scope selected</li>
            <li>• Ontology guardrails uploaded</li>
            <li>• Smoke test executed</li>
          </ul>
          <button
            type="button"
            className="mt-6 w-full rounded-lg border border-[#E57373] px-4 py-2 text-sm font-semibold text-[#E57373] transition-colors hover:bg-[#E57373] hover:text-white"
          >
            Export configuration (JSON)
          </button>
        </div>
      </section>

      <section className="rounded-2xl border border-dashed border-[#E5E7EB] bg-white p-8 text-center text-sm text-[#6B7280]">
        Prototype-only: integrate with the real configuration backend to make
        this wizard fully operational.
      </section>
    </div>
  );
}
