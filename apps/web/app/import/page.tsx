export default function ImportPage() {
  return (
    <div className="mx-auto flex max-w-5xl flex-col gap-12 px-6 py-16 text-[#1C1C1C]">
      <section className="flex flex-col gap-4 text-justify">
        <h1 className="text-3xl font-semibold">Import a Knowledge Graph</h1>
        <p className="text-base text-[#4B5563]">
          Use this prototype flow to imagine how Grape will let you bring new
          RDF, JSON-LD, or SPARQL endpoints into the platform.
        </p>
      </section>

      <section className="grid gap-6 md:grid-cols-3">
        {[
          {
            title: 'Upload RDF / JSON-LD',
            subtitle: 'Drag & drop or browse local files to seed a new workspace.',
            cta: 'Choose File',
          },
          {
            title: 'Connect SPARQL Endpoint',
            subtitle: 'Provide an HTTPS endpoint, credentials, and default graph.',
            cta: 'Add Endpoint',
          },
          {
            title: 'Load from Wikidata',
            subtitle: 'Preview a Wikidata slice (ENT + psychiatry) and push it into your workspace.',
            cta: 'Load from Wikidata',
          },
        ].map(card => (
          <div key={card.title} className="flex flex-col gap-4 rounded-2xl border border-[#E5E7EB] bg-white p-6 shadow-sm">
            <div>
              <h2 className="text-lg font-semibold text-[#1C1C1C]">{card.title}</h2>
              <p className="mt-2 text-sm text-[#4B5563] text-justify">{card.subtitle}</p>
            </div>
            <button
              type="button"
              className="mt-auto w-full rounded-lg border border-[#E57373] px-4 py-2 text-sm font-semibold text-[#E57373] transition-colors hover:bg-[#E57373] hover:text-white"
            >
              {card.cta}
            </button>
          </div>
        ))}
      </section>

      <section className="space-y-4 rounded-2xl border border-[#E5E7EB] bg-white p-6 shadow-sm">
        <div>
          <h2 className="text-lg font-semibold text-[#1C1C1C]">
            Choose your source
          </h2>
          <p className="mt-1 text-sm text-[#4B5563] text-justify">
            Upload a file, connect to a remote endpoint, or link an existing
            Grape workspace.
          </p>
        </div>
        <div>
          <h2 className="text-lg font-semibold text-[#1C1C1C]">
            Describe the ontology
          </h2>
          <p className="mt-1 text-sm text-[#4B5563] text-justify">
            Provide namespace prefixes, ontology documentation, and any custom
            inference rules you rely on.
          </p>
        </div>
        <div>
          <h2 className="text-lg font-semibold text-[#1C1C1C]">
            Validate &amp; preview
          </h2>
          <p className="mt-1 text-sm text-[#4B5563] text-justify">
            Run quick checks to confirm the graph loads correctly and produces
            meaningful neighbourhood samples.
          </p>
        </div>
      </section>

      <section className="rounded-2xl border border-dashed border-[#E5E7EB] bg-white p-8 text-center text-sm text-[#6B7280]">
        Future upgrade: plug in the real ingestion pipeline so teams can import
        production graphs from day one.
      </section>
    </div>
  );
}
