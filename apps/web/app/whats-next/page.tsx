export default function WhatsNextPage() {
  return (
    <div className="mx-auto flex max-w-4xl flex-col gap-12 px-8 py-20">
      <section className="flex flex-col gap-6">
        <h1 className="text-4xl font-bold text-left text-[#1C1C1C]">
          What's Next: From Agent to Platform
        </h1>
        <p className="text-lg leading-relaxed text-justify text-[#4B5563]">
          This hackathon project is the foundation for our larger vision. Our roadmap
          is clear.
        </p>
      </section>

      <section className="flex flex-col gap-8">
        <div className="mx-auto flex max-w-3xl flex-col gap-6">
          <div className="rounded-2xl border border-[#E5E7EB] bg-white p-8 shadow-sm">
            <h2 className="text-2xl font-semibold text-left text-[#1C1C1C]">
              1. Improve the Agent
            </h2>
            <p className="mt-4 text-lg leading-relaxed text-justify text-[#4B5563]">
              We will continue to refine the agent by adding more robust reasoning
              scenarios and enhancing the clarity of the graph visualizations, making
              the reasoning process fully transparent.
            </p>
          </div>

          <div className="rounded-2xl border border-[#E5E7EB] bg-white p-8 shadow-sm">
            <h2 className="text-2xl font-semibold text-left text-[#1C1C1C]">
              2. Build the "Grape KG Builder"
            </h2>
            <p className="mt-4 text-lg leading-relaxed text-justify text-[#4B5563]">
              This is our core mission. We will build the platform that solves the
              three great bottlenecks. We will use AI-assisted tooling to empower
              domain experts to:
            </p>
            <div className="mt-6 space-y-4">
              <p className="text-base leading-relaxed text-justify text-[#4B5563]">
                <strong className="text-[#1C1C1C]">
                  Visually Model Ontologies
                </strong>{" "}
                (without writing code).
              </p>
              <p className="text-base leading-relaxed text-justify text-[#4B5563]">
                <strong className="text-[#1C1C1C]">
                  Automate Fact Extraction
                </strong>{" "}
                (using LLMs constrained by their ontology).
              </p>
              <p className="text-base leading-relaxed text-justify text-[#4B5563]">
                <strong className="text-[#1C1C1C]">Simplify Alignment</strong> (with
                a "human-in-the-loop" validation assistant).
              </p>
            </div>
          </div>
        </div>
      </section>

      <section className="flex flex-col gap-6">
        <p className="text-lg leading-relaxed text-justify font-medium text-[#1C1C1C]">
          Grape is a work in progress, but it represents a clear path toward a
          future of trustworthy, frugal, and democratized artificial intelligence.
        </p>
      </section>

      <section className="mt-8 border-t border-[#E5E7EB] pt-8 text-center">
        <p className="text-sm italic text-[#6B7280]">Written by Léandre Ramos</p>
      </section>
    </div>
  );
}
