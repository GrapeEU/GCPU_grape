export default function HowItWorksPage() {
  return (
    <div className="mx-auto flex max-w-4xl flex-col gap-12 px-8 py-20">
      <section className="flex flex-col gap-6">
        <h1 className="text-4xl font-bold text-left text-[#1C1C1C]">
          How the "Grape" Agent Works
        </h1>
      </section>

      <section className="flex flex-col gap-6">
        <p className="text-lg leading-relaxed text-justify text-[#4B5563]">
          For this hackathon, we focused on the first piece of our vision:{" "}
          <strong>The Grape Agent</strong>.
        </p>
        <p className="text-lg leading-relaxed text-justify text-[#4B5563]">
          This agent is a reasoning engine that operates on top of a knowledge graph.
          We use a frugal LLM not for its knowledge, but as an intelligent orchestrator
          to translate human questions into logical queries.
        </p>
        <p className="text-lg leading-relaxed text-justify text-[#4B5563]">
          This "Agent-on-a-Graph" provides benefits that LLMs alone cannot:
        </p>
        <div className="mx-auto max-w-2xl space-y-4">
          <p className="text-base leading-relaxed text-justify text-[#4B5563]">
            <strong className="text-[#1C1C1C]">Zero Hallucination:</strong> Answers
            are derived from the graph's facts, not invented.
          </p>
          <p className="text-base leading-relaxed text-justify text-[#4B5563]">
            <strong className="text-[#1C1C1C]">Full Traceability:</strong> Every
            conclusion is an auditable proof.
          </p>
          <p className="text-base leading-relaxed text-justify text-[#4B5563]">
            <strong className="text-[#1C1C1C]">Frugal Power:</strong> We use a small
            LLM as a "pilot" to steer the powerful KG engine.
          </p>
        </div>
      </section>

      <section className="flex flex-col gap-6">
        <h2 className="text-2xl font-semibold text-left text-[#1C1C1C]">
          Core Reasoning Capabilities
        </h2>
        <p className="text-lg leading-relaxed text-justify text-[#4B5563]">
          The Grape agent can be dynamically configured by the LLM to perform three
          core operations:
        </p>
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
              Cross-Graph Alignment
            </h3>
            <p className="mt-3 text-base leading-relaxed text-[#4B5563]">
              <em>"Do audiology and psychiatry share any concepts?"</em> The agent
              bridges separate graphs to reveal shared risk factors or therapies,
              breaking down knowledge silos.
            </p>
          </div>
        </div>
      </section>

      <section className="flex flex-col gap-6">
        <h2 className="text-2xl font-semibold text-left text-[#1C1C1C]">
          The "Deep Reasoning" Mode
        </h2>
        <p className="text-lg leading-relaxed text-justify text-[#4B5563]">
          In this advanced mode, the user asks a complex question. The LLM agent
          doesn't just pick one scenario; it <em>combines</em> them. It might first{" "}
          <strong>Explore</strong> a concept, then <strong>Find a Path</strong> to
          another, and finally <strong>Validate</strong> a hypothesis against a third,
          all within a single, autonomous reasoning loop before returning the final,
          synthesized answer.
        </p>
      </section>

      <section className="mt-8 border-t border-[#E5E7EB] pt-8 text-center">
        <p className="text-sm italic text-[#6B7280]">Written by Léandre Ramos</p>
      </section>
    </div>
  );
}
