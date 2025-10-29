export default function ConceptPage() {
  return (
    <div className="mx-auto flex max-w-5xl flex-col gap-12 px-6 py-16 text-[#1C1C1C]">
      <section className="flex flex-col gap-5">
        <h1 className="text-3xl font-semibold">Why Knowledge Graphs Matter</h1>
        <p className="text-base text-[#4B5563] text-justify">
          A knowledge graph is a living map of concepts, people, conditions, and
          treatments. Each node represents a well-defined entity and each edge
          captures how those entities relate. Ontologies provide the grammar for
          that map: they define which relationships are allowed, how concepts
          inherit from one another, and what logical rules must hold. When we
          apply ontologies on top of the data, every inference becomes
          traceable.
        </p>
        <p className="text-base text-[#4B5563] text-justify">
          Many clinical teams still keep separate graphs for audiology,
          psychiatry, pharmaceutical research, and more. Grape links those
          islands together. By aligning vocabularies and running reasoning
          across domains, we help researchers expose hidden overlaps and
          validate hypotheses that would otherwise stay siloed.
        </p>
        <p className="text-base text-[#4B5563] text-justify">
          The result is an assistant that answers with grounded, explainable
          evidence rather than opaque predictions. Every response references the
          exact nodes, ontologies, and triples that support it.
        </p>
      </section>

      <section className="flex flex-col gap-4">
        <h2 className="text-2xl font-semibold">Four Scenarios Grape Handles</h2>
        <div className="space-y-4 rounded-2xl border border-[#E5E7EB] bg-white p-6 shadow-sm">
          <p className="text-sm text-[#4B5563] text-justify">
            <strong className="text-[#1C1C1C]">1. Neighbourhood exploration:</strong>{" "}
            surface everything related to a focus concept when you need rapid
            situational awareness.
          </p>
          <p className="text-sm text-[#4B5563] text-justify">
            <strong className="text-[#1C1C1C]">2. Multi-hop reasoning:</strong>{" "}
            follow causal or associative chains across multiple ontologies to
            uncover hidden intermediates.
          </p>
          <p className="text-sm text-[#4B5563] text-justify">
            <strong className="text-[#1C1C1C]">3. Cross-graph alignment:</strong>{" "}
            bridge separate graphs to reveal shared risk factors or therapies
            that span medical specialties.
          </p>
          <p className="text-sm text-[#4B5563] text-justify">
            <strong className="text-[#1C1C1C]">4. Formal validation:</strong>{" "}
            test a clinical assertion and retrieve the precise triples that
            prove or refute it.
          </p>
        </div>
      </section>
    </div>
  );
}
