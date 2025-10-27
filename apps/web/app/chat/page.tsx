'use client';

import { useState, useMemo, useEffect } from 'react';
import Image from 'next/image';
import Link from 'next/link';
import AgentSelector from '@/components/AgentSelector';
import ChatInterface, { ScenarioResultData } from '@/components/ChatInterface';
import GraphVisualizer from '@/components/GraphVisualizer';
import ThemeSwitcher from '@/components/ThemeSwitcher';
import { useTheme } from '@/contexts/ThemeContext';
import agents from '@/data/agents.json';

export default function ChatPage() {
  const { theme } = useTheme();
  const [selectedAgent, setSelectedAgent] = useState<string | null>(null);
  const [scenarioResult, setScenarioResult] = useState<ScenarioResultData | null>(null);

  const isDark = theme === 'dark';

  // Get KG files for the selected agent
  const kgFiles = useMemo(() => {
    if (!selectedAgent) return [];
    const agent = agents.find(a => a.id === selectedAgent);
    return agent?.kgFiles || [];
  }, [selectedAgent]);

  const handleScenarioResult = (result: ScenarioResultData | null) => {
    setScenarioResult(result);
  };

  useEffect(() => {
    setScenarioResult(null);
  }, [selectedAgent]);

  return (
    <div className={`flex flex-col h-screen ${isDark ? 'bg-[#0F1419]' : 'bg-[#FDFDFD]'}`}>
      {/* Top Bar with Agent Selector */}
      <div className={`px-6 py-4 border-b ${isDark ? 'bg-[#1C1C1C] border-[#374151]' : 'bg-white border-[#E5E7EB]'}`}>
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-4">
            <h1 className={`text-xl font-semibold ${isDark ? 'text-white' : 'text-[#1C1C1C]'}`}>
              Chat with Agent
            </h1>
            <AgentSelector
              selectedAgent={selectedAgent}
              onSelectAgent={setSelectedAgent}
            />
          </div>
          <div className="flex items-center gap-3">
            <ThemeSwitcher />
            <Link href="/" className="flex items-center gap-2 hover:opacity-80 transition-opacity">
              <Image
                src="/grape_logo.png"
                alt="Grape Logo"
                width={40}
                height={40}
                priority
                className={isDark ? 'invert' : ''}
              />
              <span className={`text-lg font-semibold ${isDark ? 'text-white' : 'text-[#1C1C1C]'}`}>Grape</span>
            </Link>
          </div>
        </div>
      </div>

      {/* Main Content - Split View */}
      <div className="flex-1 flex overflow-hidden">
        {/* Left Panel - Graph Visualizer */}
        <div className={`w-1/2 border-r p-6 ${isDark ? 'border-[#374151]' : 'border-[#E5E7EB]'}`}>
          <GraphVisualizer kgFiles={kgFiles} scenarioData={scenarioResult} />
        </div>

        {/* Right Panel - Chat Interface */}
        <div className="w-1/2 p-6 space-y-4 overflow-y-auto">
          {scenarioResult && (
            <div className={`rounded-lg border px-5 py-4 ${isDark ? 'bg-[#111827] border-[#374151]' : 'bg-white border-[#E5E7EB]'}`}>
              <h3 className={`text-sm font-semibold ${isDark ? 'text-white' : 'text-[#1C1C1C]'}`}>
                Scenario • {scenarioResult.title}
              </h3>
              <p className={`mt-2 text-sm ${isDark ? 'text-[#E5E7EB]' : 'text-[#1C1C1C]'}`}>
                {scenarioResult.summary}
              </p>
              {scenarioResult.trace.length > 0 && (
                <ul className={`mt-3 space-y-1 text-xs ${isDark ? 'text-[#9CA3AF]' : 'text-[#4B5563]'}`}>
                  {scenarioResult.trace.map((item, index) => (
                    <li key={index}>• {item}</li>
                  ))}
                </ul>
              )}
            </div>
          )}

          <ChatInterface
            selectedAgent={selectedAgent}
            onScenarioResult={handleScenarioResult}
          />
        </div>
      </div>
    </div>
  );
}
