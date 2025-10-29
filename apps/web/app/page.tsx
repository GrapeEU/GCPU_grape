import Image from "next/image";
import Link from "next/link";

const actions = [
  {
    href: "/import",
    title: "Import a Knowledge Graph",
    description:
      "Upload RDF or connect an existing endpoint to seed Grape with your domain data.",
    icon: (
      <svg
        className="h-8 w-8 text-[#E57373]"
        viewBox="0 0 24 24"
        fill="none"
        stroke="currentColor"
      >
        <path
          strokeLinecap="round"
          strokeLinejoin="round"
          strokeWidth={1.8}
          d="M12 4v16m8-8H4"
        />
      </svg>
    ),
  },
  {
    href: "/finetune",
    title: "Finetune the Agent",
    description:
      "Guide the assistant with your ontologies, guardrails, and preferred reasoning patterns.",
    icon: (
      <svg
        className="h-8 w-8 text-[#F59E0B]"
        viewBox="0 0 24 24"
        fill="none"
        stroke="currentColor"
      >
        <path
          strokeLinecap="round"
          strokeLinejoin="round"
          strokeWidth={1.8}
          d="M11 17a4 4 0 01-4-4V5a4 4 0 018 0v8a4 4 0 01-4 4zm0 0v3m-4 0h8"
        />
      </svg>
    ),
  },
  {
    href: "/chat",
    title: "Chat with the Agent",
    description:
      "Ask clinical questions and review transparent, ontology-backed reasoning in real time.",
    icon: (
      <svg
        className="h-8 w-8 text-[#10B981]"
        viewBox="0 0 24 24"
        fill="none"
        stroke="currentColor"
      >
        <path
          strokeLinecap="round"
          strokeLinejoin="round"
          strokeWidth={1.8}
          d="M8 10h.01M12 10h.01M16 10h.01M9 16H5a2 2 0 01-2-2V6a2 2 0 012-2h14a2 2 0 012 2v8a2 2 0 01-2 2h-5l-5 5v-5z"
        />
      </svg>
    ),
  },
];

const graphNodes = [
  { id: "node1", x: 30, y: 52, label: "Tinnitus" },
  { id: "node2", x: 65, y: 22, label: "Hearing Loss" },
  { id: "node3", x: 85, y: 58, label: "Sleep Disturbance" },
  { id: "node4", x: 48, y: 80, label: "Stress" },
  { id: "node5", x: 15, y: 28, label: "CBT" },
];

const graphEdges: Array<[string, string]> = [
  ["node1", "node2"],
  ["node1", "node3"],
  ["node2", "node3"],
  ["node4", "node1"],
  ["node4", "node2"],
  ["node5", "node4"],
];

function GraphPreview() {
  return (
    <div className="relative mx-auto mt-8 w-full max-w-xl rounded-3xl p-6">
      <svg viewBox="0 0 100 100" className="h-56 w-full text-[#CBD5F5]">
        {graphEdges.map(([sourceId, targetId]) => {
          const source = graphNodes.find((node) => node.id === sourceId);
          const target = graphNodes.find((node) => node.id === targetId);
          if (!source || !target) return null;
          return (
            <line
              key={`${source.id}-${target.id}`}
              x1={source.x}
              y1={source.y}
              x2={target.x}
              y2={target.y}
              stroke="currentColor"
              strokeWidth={1.2}
              strokeLinecap="round"
              className="opacity-70"
            />
          );
        })}
        {graphNodes.map((node) => (
          <g key={node.id}>
            <circle
              cx={node.x}
              cy={node.y}
              r={4.2}
              fill="#E57373"
              className="drop-shadow-sm"
            />
            <text
              x={node.x}
              y={node.y + 7}
              textAnchor="middle"
              fontSize={4}
              fill="#6B7280"
            >
              {node.label}
            </text>
          </g>
        ))}
      </svg>
      <p className="mt-4 text-center text-xs text-[#6B7280]">
        Demo graph highlight: how symptoms, risks, and treatments remain linked
        across ontologies.
      </p>
    </div>
  );
}

export default function Home() {
  return (
    <div className="flex flex-col items-center px-6 py-16">
      <section className="flex w-full max-w-5xl flex-col items-center gap-8 text-center">
        <Image
          src="/grape_logo.png"
          alt="Grape Logo"
          width={140}
          height={140}
          priority
        />
        <p className="max-w-3xl text-lg text-[#4B5563]">
          Grape connects medical knowledge across disciplines. We expose the
          structure behind every answer so researchers and clinicians can trust
          what the agent finds in their graphs.
        </p>
        <GraphPreview />
      </section>

      <section className="mt-16 grid w-full max-w-5xl gap-6 md:grid-cols-3">
        {actions.map(({ href, title, description, icon }) => (
          <Link
            key={href}
            href={href}
            className="group flex flex-col gap-4 rounded-2xl border border-[#E5E7EB] bg-white p-8 shadow-sm transition-transform hover:-translate-y-1 hover:shadow-lg"
          >
            <div className="flex items-center justify-center">{icon}</div>
            <h2 className="text-xl font-semibold text-[#1C1C1C]">{title}</h2>
            <p className="text-sm leading-relaxed text-[#6B7280]">
              {description}
            </p>
            <span className="mt-auto text-sm font-medium text-[#E57373] group-hover:underline">
              Get started →
            </span>
          </Link>
        ))}
      </section>
    </div>
  );
}
