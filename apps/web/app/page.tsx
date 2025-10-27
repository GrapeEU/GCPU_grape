import Image from "next/image";
import Link from "next/link";

export default function Home() {
  return (
    <div className="flex min-h-screen flex-col items-center justify-center bg-[#FDFDFD] px-4">
      <main className="flex w-full max-w-4xl flex-col items-center gap-12 text-center">
        {/* Logo */}
        <div className="flex flex-col items-center gap-6">
          <Image
            src="/grape_logo.png"
            alt="Grape Logo"
            width={120}
            height={120}
            priority
          />
          <div>
            <h1 className="text-5xl font-bold text-[#1C1C1C] mb-4">
              Welcome to Grape
            </h1>
            <p className="text-xl text-[#6B7280] max-w-2xl">
              AI-powered knowledge graph visualization and querying platform
            </p>
          </div>
        </div>

        {/* Features */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-8 w-full mt-8">
          <div className="bg-white p-6 rounded-lg border border-[#E5E7EB]">
            <div className="text-[#E57373] mb-3">
              <svg
                className="w-10 h-10 mx-auto"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z"
                />
              </svg>
            </div>
            <h3 className="text-lg font-semibold text-[#1C1C1C] mb-2">
              Interactive Visualization
            </h3>
            <p className="text-sm text-[#6B7280]">
              Explore your knowledge graphs with intuitive pan, zoom, and click interactions
            </p>
          </div>

          <div className="bg-white p-6 rounded-lg border border-[#E5E7EB]">
            <div className="text-[#E57373] mb-3">
              <svg
                className="w-10 h-10 mx-auto"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M8 10h.01M12 10h.01M16 10h.01M9 16H5a2 2 0 01-2-2V6a2 2 0 012-2h14a2 2 0 012 2v8a2 2 0 01-2 2h-5l-5 5v-5z"
                />
              </svg>
            </div>
            <h3 className="text-lg font-semibold text-[#1C1C1C] mb-2">
              AI-Powered Querying
            </h3>
            <p className="text-sm text-[#6B7280]">
              Ask natural language questions and get verifiable answers from your data
            </p>
          </div>

          <div className="bg-white p-6 rounded-lg border border-[#E5E7EB]">
            <div className="text-[#E57373] mb-3">
              <svg
                className="w-10 h-10 mx-auto"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M13 7h8m0 0v8m0-8l-8 8-4-4-6 6"
                />
              </svg>
            </div>
            <h3 className="text-lg font-semibold text-[#1C1C1C] mb-2">
              Transparent Reasoning
            </h3>
            <p className="text-sm text-[#6B7280]">
              See the complete reasoning path the AI took to answer your questions
            </p>
          </div>
        </div>

        {/* CTA Buttons */}
        <div className="mt-8 flex flex-col sm:flex-row gap-4">
          <Link
            href="/workspace"
            className="inline-flex items-center gap-2 px-8 py-4 bg-[#E57373] text-white text-lg font-semibold rounded-lg hover:bg-[#D55555] transition-colors"
          >
            Open Workspace
            <svg
              className="w-5 h-5"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M13 7l5 5m0 0l-5 5m5-5H6"
              />
            </svg>
          </Link>
          <Link
            href="/chat"
            className="inline-flex items-center gap-2 px-8 py-4 border-2 border-[#E57373] text-[#E57373] text-lg font-semibold rounded-lg hover:bg-[#E57373] hover:text-white transition-colors"
          >
            <svg
              className="w-5 h-5"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M8 10h.01M12 10h.01M16 10h.01M9 16H5a2 2 0 01-2-2V6a2 2 0 012-2h14a2 2 0 012 2v8a2 2 0 01-2 2h-5l-5 5v-5z"
              />
            </svg>
            Chat with Agent
          </Link>
        </div>

        {/* Secondary Actions */}
        <div className="flex flex-col sm:flex-row gap-4 mt-4">
          <button
            className="px-6 py-3 border border-[#E5E7EB] text-[#1C1C1C] rounded-lg hover:bg-white transition-colors"
            disabled
          >
            Import RDF File
          </button>
          <button
            className="px-6 py-3 border border-[#E5E7EB] text-[#1C1C1C] rounded-lg hover:bg-white transition-colors"
            disabled
          >
            Create from PDF
          </button>
          <button
            className="px-6 py-3 border border-[#E5E7EB] text-[#1C1C1C] rounded-lg hover:bg-white transition-colors"
            disabled
          >
            Create from URL
          </button>
        </div>
      </main>
    </div>
  );
}
