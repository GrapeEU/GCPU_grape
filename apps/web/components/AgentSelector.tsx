'use client';

import { useState, useEffect, useRef } from 'react';
import agents from '@/data/agents.json';

interface AgentSelectorProps {
  selectedAgent: string | null;
  onSelectAgent: (agentId: string) => void;
}

export default function AgentSelector({ selectedAgent, onSelectAgent }: AgentSelectorProps) {
  const [isOpen, setIsOpen] = useState(false);
  const dropdownRef = useRef<HTMLDivElement>(null);

  const currentAgent = agents.find(a => a.id === selectedAgent);

  useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target as Node)) {
        setIsOpen(false);
      }
    }

    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  return (
    <div className="relative" ref={dropdownRef}>
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="flex items-center gap-2 px-4 py-2 bg-white border border-[#E5E7EB] rounded-lg hover:bg-[#FDFDFD] transition-colors text-sm"
      >
        <svg
          className="w-4 h-4 text-[#6B7280]"
          fill="none"
          stroke="currentColor"
          viewBox="0 0 24 24"
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth={2}
            d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z"
          />
        </svg>
        <span className="text-[#1C1C1C] font-medium">
          {currentAgent ? currentAgent.name : 'Select Agent'}
        </span>
        <svg
          className={`w-4 h-4 text-[#6B7280] transition-transform ${isOpen ? 'rotate-180' : ''}`}
          fill="none"
          stroke="currentColor"
          viewBox="0 0 24 24"
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth={2}
            d="M19 9l-7 7-7-7"
          />
        </svg>
      </button>

      {isOpen && (
        <div className="absolute top-full left-0 mt-2 w-64 bg-white border border-[#E5E7EB] rounded-lg shadow-lg z-50 overflow-hidden">
          {agents.map((agent) => (
            <button
              key={agent.id}
              onClick={() => {
                onSelectAgent(agent.id);
                setIsOpen(false);
              }}
              className={`w-full px-4 py-3 text-left hover:bg-[#FDFDFD] transition-colors border-b border-[#E5E7EB] last:border-b-0 ${
                selectedAgent === agent.id ? 'bg-[#FEF3F3]' : ''
              }`}
            >
              <div className="flex items-center gap-3">
                <div className={`w-2 h-2 rounded-full ${
                  selectedAgent === agent.id ? 'bg-[#E57373]' : 'bg-[#E5E7EB]'
                }`} />
                <div className="flex-1">
                  <div className="font-medium text-[#1C1C1C] text-sm">
                    {agent.name}
                  </div>
                  <div className="text-xs text-[#6B7280] mt-0.5 line-clamp-2">
                    {agent.prompt}
                  </div>
                </div>
              </div>
            </button>
          ))}
        </div>
      )}
    </div>
  );
}
