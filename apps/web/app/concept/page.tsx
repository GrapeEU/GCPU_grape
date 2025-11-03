export default function ConceptPage() {
  return (
    <div className="mx-auto flex max-w-4xl flex-col gap-12 px-8 py-20">
      <section className="flex flex-col gap-6">
        <h1 className="text-4xl font-bold text-left text-[#1C1C1C]">
          The Future of AI Needs a Verifiable Brain
        </h1>
      </section>

      <section className="flex flex-col gap-6">
        <h2 className="text-2xl font-semibold text-left text-[#1C1C1C]">
          The Web's Unfinished Dream
        </h2>
        <p className="text-lg leading-relaxed text-justify text-[#4B5563]">
          When Tim Berners-Lee envisioned the "Semantic Web," his dream wasn't just
          to link documents. It was to link <em>data</em>. He imagined a web where
          machines could understand the meaning and context of information, enabling
          true, logical reasoning.
        </p>
        <p className="text-lg leading-relaxed text-justify text-[#4B5563]">
          For decades, this power remained locked away, accessible only to semantic experts.
        </p>
      </section>

      <section className="flex flex-col gap-6">
        <h2 className="text-2xl font-semibold text-left text-[#1C1C1C]">
          The Power of Reasoning vs. Guessing
        </h2>
        <p className="text-lg leading-relaxed text-justify text-[#4B5563]">
          Large Language Models (LLMs) are powerful text generators, but they predict
          the next word. They don't <em>know</em> what's true. This is why they hallucinate.
        </p>
        <p className="text-lg leading-relaxed text-justify text-[#4B5563]">
          A Knowledge Graph (KG) operates differently. It runs on logical inference.
        </p>
        <div className="mx-auto max-w-2xl space-y-3 rounded-2xl border border-[#E5E7EB] bg-white p-8 text-left shadow-sm">
          <p className="font-mono text-sm text-[#374151]">
            <strong>Fact 1:</strong> (Socrates) -[is a]-&gt; (Man)
          </p>
          <p className="font-mono text-sm text-[#374151]">
            <strong>Fact 2:</strong> (Man) -[is a]-&gt; (Mortal)
          </p>
          <p className="font-mono text-sm font-semibold text-[#1C1C1C]">
            <strong>Inference:</strong> The graph logically deduces a new, verifiable truth:{" "}
            (Socrates) -[is a]-&gt; (Mortal).
          </p>
        </div>
        <p className="text-lg leading-relaxed text-justify text-[#4B5563]">
          This isn't a guess. It's a traceable, auditable <em>proof</em>.
        </p>
      </section>

      <section className="flex flex-col gap-6">
        <h2 className="text-2xl font-semibold text-left text-[#1C1C1C]">
          The Bottleneck: The "Expert" Problem
        </h2>
        <p className="text-lg leading-relaxed text-justify text-[#4B5563]">
          If KGs are so powerful, why isn't this the standard?
        </p>
        <p className="text-lg leading-relaxed text-justify text-[#4B5563]">
          Because building them is incredibly difficult. Today, creating a KG requires
          an army of semantic engineers to:
        </p>
        <div className="mx-auto max-w-2xl space-y-4">
          <p className="text-base leading-relaxed text-justify text-[#4B5563]">
            <strong className="text-[#1C1C1C]">Model the Ontology:</strong> Manually
            define the "rules of the world" (what is a "Symptom"? what is a "Gene"?).
          </p>
          <p className="text-base leading-relaxed text-justify text-[#4B5563]">
            <strong className="text-[#1C1C1C]">Extract the Facts:</strong> Laboriously
            pull data from siloed databases, PDFs, and text.
          </p>
          <p className="text-base leading-relaxed text-justify text-[#4B5563]">
            <strong className="text-[#1C1C1C]">Align & Validate:</strong> Cleanly map
            concepts together (e.g., ensuring "Paracetamol" and "Acetaminophen" are
            the same <code className="rounded bg-gray-100 px-1.5 py-0.5 font-mono text-xs">owl:sameAs</code> entity).
          </p>
        </div>
        <p className="text-lg leading-relaxed text-justify text-[#4B5563]">
          This bottleneck has kept trustworthy AI out of the hands of those who need it most.
        </p>
      </section>

      <section className="flex flex-col gap-6">
        <h2 className="text-2xl font-semibold text-left text-[#1C1C1C]">
          Our Vision: The Frugal, Trustworthy AI Stack
        </h2>
        <p className="text-lg leading-relaxed text-justify text-[#4B5563]">
          We believe the solution is to separate the <em>brain</em> from the <em>parrot</em>.
        </p>
        <p className="text-lg leading-relaxed text-justify text-[#4B5563]">
          Let LLMs do what they do best: understand and generate human language. Let a
          Knowledge Graph do what it does best: store facts, manage rules, and perform
          logical reasoning.
        </p>
        <p className="text-lg leading-relaxed text-justify text-[#4B5563]">
          Our mission is to democratize this stack. We are building the tools to solve
          the creation bottleneck, enabling any expert to build their own "verifiable brain."
          This allows for smaller, frugal, and safer AI that doesn't hallucinate, because
          its reasoning is auditable, controllable, and grounded in fact.
        </p>
      </section>

      <section className="mt-8 border-t border-[#E5E7EB] pt-8 text-center">
        <p className="text-sm italic text-[#6B7280]">Written by Léandre Ramos</p>
      </section>
    </div>
  );
}
