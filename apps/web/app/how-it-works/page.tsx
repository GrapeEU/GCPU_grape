const scenarioExamples = [
  {
    title: "Neighbourhood exploration",
    question: "“What relations surround Tinnitus in the hearing graph?”",
  },
  {
    title: "Multi-hop reasoning",
    question:
      "“How does Chronic Stress lead to Hearing Loss through intermediate conditions?”",
  },
  {
    title: "Cross-graph alignment",
    question:
      "“Are there shared risk factors between Tinnitus and Generalized Anxiety Disorder?”",
  },
  {
    title: "Formal validation",
    question:
      "“Does cognitive behavioral therapy help with Hearing Loss according to the graph?”",
  },
];

export default function HowItWorksPage() {
  return (
    <div className="mx-auto flex max-w-5xl flex-col gap-12 px-6 py-16 text-[#1C1C1C]">
      <section className="flex flex-col gap-4">
        <h1 className="text-3xl font-semibold">How Grape Works</h1>
        <p className="text-base text-[#4B5563] text-justify">
          Grape follows a repeatable reasoning loop. Each stage is transparent,
          so clinicians can inspect the inputs, the queries, and the evidence
          before trusting the answer. The same backbone powers the live agent
          and the demo scenarios showcased in the PoC.
        </p>
      </section>

      <section className="grid gap-6 md:grid-cols-2">
        <div className="rounded-2xl border border-[#E5E7EB] bg-white p-6 shadow-sm">
          <h2 className="text-lg font-semibold text-[#1C1C1C]">Step 1</h2>
          <p className="mt-2 text-sm text-[#4B5563] text-justify">
            Detect key medical entities in the question and resolve them to
            their canonical URIs inside the graph. This guarantees we operate on
            precise, ontology-backed concepts.
          </p>
        </div>
        <div className="rounded-2xl border border-[#E5E7EB] bg-white p-6 shadow-sm">
          <h2 className="text-lg font-semibold text-[#1C1C1C]">Step 2</h2>
          <p className="mt-2 text-sm text-[#4B5563] text-justify">
            Generate the SPARQL query best suited for the scenario—neighbourhood
            lookup, multi-hop path search, federated alignment, or validation of
            a claim.
          </p>
        </div>
        <div className="rounded-2xl border border-[#E5E7EB] bg-white p-6 shadow-sm">
          <h2 className="text-lg font-semibold text-[#1C1C1C]">Step 3</h2>
          <p className="mt-2 text-sm text-[#4B5563] text-justify">
            Execute the query against the graph database. Ontological reasoning
            layers infer additional triples, helping reveal implicit links and
            shared semantics across repositories.
          </p>
        </div>
        <div className="rounded-2xl border border-[#E5E7EB] bg-white p-6 shadow-sm">
          <h2 className="text-lg font-semibold text-[#1C1C1C]">Step 4</h2>
          <p className="mt-2 text-sm text-[#4B5563] text-justify">
            Interpret the results: we display the nodes/links for inspection and
            deliver a concise, human-readable explanation grounded in those
            triples. No hallucinations—only verifiable evidence.
          </p>
        </div>
      </section>

      <section className="flex flex-col gap-4">
        <h2 className="text-2xl font-semibold">
          Demo Scenarios &amp; Starter Questions
        </h2>
        <div className="grid gap-4 rounded-2xl border border-[#E5E7EB] bg-white p-6 shadow-sm md:grid-cols-2">
          {scenarioExamples.map(({ title, question }) => (
            <div key={title} className="space-y-2">
              <p className="text-sm font-semibold text-[#1C1C1C]">{title}</p>
              <p className="text-xs text-[#4B5563] text-justify">{question}</p>
            </div>
          ))}
        </div>
      </section>

      <section className="rounded-2xl border border-dashed border-[#E5E7EB] bg-white p-8 text-center text-sm text-[#6B7280]">
        Diagram placeholder: entity detection → SPARQL generation → ontological
        reasoning → interpreted answer.
      </section>
    </div>
  );
}
