export default function HowItWorksPage() {
  return (
    <div className="mx-auto flex max-w-4xl flex-col gap-12 px-8 py-20">
      <section className="flex flex-col gap-6">
        <h1 className="text-4xl font-bold text-left text-[#1C1C1C]">
          How Grape Works: Language ↔ Logic
        </h1>
      </section>

      <section className="flex flex-col gap-6">
        <p className="text-lg leading-relaxed text-justify text-[#4B5563]">
          Many believe we’re entering the decade of AI agents. But agents only
          work if we can <em>trust</em> them. Grape tackles trust by cleanly
          separating the LLM (language) from the Knowledge Graph (logic).
        </p>
        <p className="text-lg leading-relaxed text-justify text-[#4B5563]">
          In this demo, the agent reasons over a federated graph built from three
          sources: <strong>Patient data</strong>, <strong>Drug & composition</strong>,
          and <strong>Public medical knowledge</strong>.
        </p>
        <p className="text-lg leading-relaxed text-justify text-[#4B5563]">
          The LLM acts as a smart pilot that interprets your question. The
          Knowledge Graph—bound by an ontology—does the reasoning and provides
          a proof you can inspect.
        </p>
        <p className="text-lg leading-relaxed text-justify text-[#4B5563]">
          Why this matters compared to RAG or Graph‑RAG:
        </p>
        <div className="mx-auto max-w-2xl space-y-4">
          <p className="text-base leading-relaxed text-justify text-[#4B5563]"><strong className="text-[#1C1C1C]">RAG</strong> grounds answers in text, but does not explain <em>why</em> a relation holds.</p>
          <p className="text-base leading-relaxed text-justify text-[#4B5563]"><strong className="text-[#1C1C1C]">Graph‑RAG</strong> finds connections, but still lacks formal proofs.</p>
          <p className="text-base leading-relaxed text-justify text-[#4B5563]"><strong className="text-[#1C1C1C]">Grape</strong> uses ontology rules to <em>prove</em> conclusions—transparent and auditable.</p>
        </div>
      </section>

      <section className="flex flex-col gap-6">
        <h2 className="text-2xl font-semibold text-left text-[#1C1C1C]">
          Core Reasoning Capabilities
        </h2>
        <p className="text-lg leading-relaxed text-justify text-[#4B5563]">The agent navigates your graph with three tools:</p>
        <div className="mx-auto flex max-w-3xl flex-col gap-6 text-left">
          <div className="rounded-2xl border border-[#E5E7EB] bg-white p-6 shadow-sm">
            <h3 className="text-lg font-semibold text-[#1C1C1C]">
              Neighbourhood Exploration
            </h3>
            <p className="mt-3 text-base leading-relaxed text-[#4B5563]">
              <em>"What's related to Tinnitus?"</em> The agent maps the immediate
              symptoms, treatments, and risk factors around a single concept.
            </p>
          </div>
          <div className="rounded-2xl border border-[#E5E7EB] bg-white p-6 shadow-sm">
            <h3 className="text-lg font-semibold text-[#1C1C1C]">
              Multi-Hop Path Finding
            </h3>
            <p className="mt-3 text-base leading-relaxed text-[#4B5563]">
              <em>"How is Chronic Stress linked to Hearing Loss?"</em> The agent finds
              the non-obvious chain of relationships that connects two concepts, even
              across different medical domains (e.g., Stress → Sleep Disturbance →
              Tinnitus).
            </p>
          </div>
          <div className="rounded-2xl border border-[#E5E7EB] bg-white p-6 shadow-sm">
            <h3 className="text-lg font-semibold text-[#1C1C1C]">
              Verifier (Ontology‑based proof)
            </h3>
            <p className="mt-3 text-base leading-relaxed text-[#4B5563]">
              Applies ontology rules to validate new facts. Example rule: side effects
              of a sub‑sequence are side effects of the parent drug.
            </p>
          </div>
        </div>
      </section>

      <section className="flex flex-col gap-6">
        <h2 className="text-2xl font-semibold text-left text-[#1C1C1C]">
          The "Deep Reasoning" Mode
        </h2>
        <p className="text-lg leading-relaxed text-justify text-[#4B5563]">
          Ask a complex question and the agent autonomously chains the tools.
          Example: a diabetic patient on Metformin reports abdominal pain. The agent
          explores Metformin, finds a path to a chemical sub‑sequence (E27B), then
          uses the Verifier to apply the ontology rule: side effects of a sub‑sequence
          are side effects of the parent drug. The proof graph supports the conclusion.
        </p>
      </section>

      <section className="mt-8 border-t border-[#E5E7EB] pt-8 text-center">
        <p className="text-sm italic text-[#6B7280]">Written by Léandre Ramos</p>
      </section>
    </div>
  );
}
