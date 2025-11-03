'use client';

import { useState, useRef, useEffect } from 'react';

import ReactMarkdown from 'react-markdown';

interface Message {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  timestamp: Date;
  markdown?: boolean;
  details?: string[];
}

export interface ScenarioResultData {
  title: string;
  summary: string;
  nodes: Array<{ id: string; label?: string; type?: string }>;
  links: Array<{ source: string; target: string; label?: string }>;
  trace: string[];
  repo: string | null;
  graph_steps?: Array<{
    title: string;
    nodes: Array<{ id: string; label?: string; type?: string }>;
    links: Array<{ source: string; target: string; label?: string }>;
  }>;
}

interface ChatInterfaceProps {
  selectedAgent: string | null;
  onScenarioResult?: (data: ScenarioResultData | null) => void;
}

const agentKgMap: Record<string, string> = {
  'medical-expert': 'grape_unified',
};

const repoFromKg = (kgName: string | null | undefined) => {
  if (!kgName) return null;
  return kgName.startsWith('grape_') ? kgName.replace('grape_', '') : kgName;
};

type Mode = 'ask' | 'agent-auto' | 'demo-s1' | 'demo-s2' | 'demo-s3' | 'deep';

const MODE_CONFIG: Record<Mode, {
  label: string;
  helper: string;
  prefill?: string;
  demoId?: string;
  kg?: string;
}> = {
  ask: {
    label: 'Ask (LLM only)',
    helper: 'Conversation libre avec le LLM, sans requête SPARQL.',
    prefill: '',
  },
  'agent-auto': {
    label: 'Agent – Auto Scenario',
    helper: 'Analyse automatique : détection du meilleur scénario KG.',
    prefill: '',
  },
  'demo-s1': {
    label: 'Agent › Patient Explorer',
    helper: 'Pipeline S1 : exploration du dossier patient.',
    prefill: "Could you review PatientJohn's chart and summarise his relevant history, symptoms, and medications?",
    demoId: 'S1_PATIENT',
    kg: 'grape_unified',
  },
  'demo-s2': {
    label: 'Agent › Path Finder',
    helper: 'Pipeline S2 : recherche de liens multi-sauts.',
    prefill: "Please investigate any hidden pathways linking substance E27B to the abdominal pain experienced by PatientJohn.",
    demoId: 'S2_PATHFINDING',
    kg: 'grape_unified',
  },
  'demo-s3': {
    label: 'Agent › Risk Verificator',
    helper: 'Pipeline S3 : validation ontologique.',
    prefill: "Given PatientJohn's nephrectomy in 2005, can you confirm whether Metamorphine is contraindicated and recommend a safer option?",
    demoId: 'S3_VALIDATION',
    kg: 'grape_unified',
  },
  deep: {
    label: 'Deep Reasoning',
    helper: 'Pipeline complète (S1→S3) avec narration détaillée.',
    prefill: "I have a diabetic patient, PatientJohn, currently on Metamorphine who now reports abdominal pain. Please investigate the risk and suggest a safer alternative.",
    demoId: 'DEEP_REASONING',
    kg: 'grape_unified',
  },
};

const scenarioProgressMap: Record<string, string[]> = {
  scenario_1_neighbourhood: [
    'Étape 1 – Détection des concepts clés…',
    'Étape 2 – Construction de la requête SPARQL…',
    'Étape 3 – Synthèse des voisins médicaux…',
  ],
  scenario_2_multihop: [
    'Étape 1 – Ancrage source / cible…',
    'Étape 2 – Exploration des chemins multi-sauts…',
    'Étape 3 – Analyse des intermédiaires critiques…',
  ],
  scenario_4_validation: [
    'Étape 1 – Vérification des contre-indications…',
    'Étape 2 – Analyse des triples probants…',
    'Étape 3 – Synthèse avec recommandation clinique…',
  ],
  DEMO_S1_PATIENT: [
    'Étape 1 – Ouverture du dossier PatientJohn…',
    'Étape 2 – Extraction des faits cliniques…',
    'Étape 3 – Préparation de la restitution…',
  ],
  DEMO_S2_PATHFINDING: [
    'Étape 1 – Analyse de la substance active E27B…',
    'Étape 2 – Recherche de liens vers la douleur abdominale…',
    'Étape 3 – Sélection des trajectoires significatives…',
  ],
  DEMO_S3_VALIDATION: [
    'Étape 1 – Vérification des contre-indications post-néphrectomie…',
    'Étape 2 – Évaluation des alternatives disponibles…',
    'Étape 3 – Préparation du verdict clinique…',
  ],
  DEMO_AUTONOMOUS: [
    'Phase 1 – Patient & traitement…',
    'Phase 2 – Substance & effets secondaires…',
    'Phase 3 – Incompatibilité & alternative…',
  ],
  DEMO_DEEP_REASONING: [
    'Phase 1 – Collecte exhaustive des indices…',
    'Phase 2 – Chaînage multi-sauts et effets rénaux…',
    'Phase 3 – Verdict ontologique et plan d’action…',
  ],
};

export default function ChatInterface({ selectedAgent, onScenarioResult }: ChatInterfaceProps) {
  const apiBaseUrl = process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:8000';
  const [messages, setMessages] = useState<Message[]>([]);
  const [inputValue, setInputValue] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [mode, setMode] = useState<Mode>('agent-auto');
  const [modeMenuOpen, setModeMenuOpen] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const modeMenuRef = useRef<HTMLDivElement>(null);
  const currentModeConfig = MODE_CONFIG[mode];
  const requiresAgent = mode === 'ask' || mode === 'agent-auto';
  const textareaPlaceholder = requiresAgent && !selectedAgent
    ? 'Sélectionnez un agent puis saisissez votre message...'
    : 'Saisissez votre message ou ajustez le prompt pré-rempli...';

const makeMessage = (role: 'user' | 'assistant', content: string, extras: Partial<Message> = {}): Message => ({
  id: `${role}-${Date.now()}-${Math.random().toString(36).slice(2)}`,
  role,
  content,
  timestamp: new Date(),
  ...extras,
});

const appendAssistantMessage = (content: string, options?: { markdown?: boolean; details?: string[] }) => {
  setMessages(prev => [
    ...prev,
    makeMessage('assistant', content, {
      markdown: options?.markdown,
      details: options?.details,
    }),
  ]);
};

  const wait = (ms: number) => new Promise(resolve => setTimeout(resolve, ms));

  const applyMode = (newMode: Mode) => {
    setMode(newMode);
    setModeMenuOpen(false);
    const config = MODE_CONFIG[newMode];
    if (typeof config.prefill === 'string') {
      setInputValue(config.prefill);
    } else if (newMode === 'ask' || newMode === 'agent-auto') {
      setInputValue('');
    }
    onScenarioResult?.(null);
  };

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      if (modeMenuRef.current && !modeMenuRef.current.contains(event.target as Node)) {
        setModeMenuOpen(false);
      }
    }
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  useEffect(() => {
    const source = new EventSource(`${apiBaseUrl}/api/agent/status-stream`);

    source.onmessage = (event) => {
      const text = (event.data || '').trim();
      if (!text) return;
      setMessages(prev => [
        ...prev,
        makeMessage('assistant', text)
      ]);
    };

    source.onerror = () => {
      source.close();
    };

    return () => {
      source.close();
    };
  }, [apiBaseUrl]);

  const executeScenario = async (
    question: string,
    kgName: string,
    scenarioIdOverride: string | null = null,
    demoId: string | null = null,
  ) => {
    try {
      const response = await fetch(`${apiBaseUrl}/api/agent/query`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          question,
          kg_name: kgName,
          ...(scenarioIdOverride ? { scenario_id: scenarioIdOverride } : {}),
          ...(demoId ? { demo_id: demoId } : {}),
        }),
      });

      if (!response.ok) {
        throw new Error('Failed scenario execution');
      }

      const payload = await response.json();
      const repoName = repoFromKg(kgName);
      const scenarioId: string = payload.scenario_used || '';
      const progressSteps = scenarioProgressMap[scenarioId] || [
        'Step 1 – Analysing the question context…',
        'Step 2 – Preparing graph reasoning steps…',
        'Step 3 – Consolidating the final answer…',
      ];
      const isDemoScenario = scenarioId.startsWith('DEMO_');

      const introMessage = demoId
        ? `${payload.scenario_name} pipeline starting...`
        : scenarioIdOverride
            ? `Scenario ${payload.scenario_name} manually triggered. Initializing pipeline...`
            : `Scenario detected (${payload.scenario_name}). Initialising analysis pipeline...`;

      appendAssistantMessage(introMessage);
      if (!isDemoScenario) {
        for (const step of progressSteps) {
          await wait(300);
          appendAssistantMessage(step);
        }
      }

      await wait(300);

      const traceLines: string[] = Array.isArray(payload.trace_formatted)
        ? payload.trace_formatted
            .map((step: any) => (step?.message || '').toString().trim())
            .filter(Boolean)
        : [];

      const nodes = Array.isArray(payload.nodes)
        ? payload.nodes.map((node: any) => ({
            id: node.id,
            label: node.label || (typeof node.id === 'string' ? node.id.split(/[/#]/).pop() : node.id),
            type: node.type,
          }))
        : [];

      const links = Array.isArray(payload.links)
        ? payload.links.map((link: any) => ({
            source: link.source,
            target: link.target,
            label: link.relation || link.label || '',
          }))
        : [];

      const summaryText = payload.answer || payload.summary || payload.response_text || '';
      const summaryLines = [
        `## ${payload.scenario_name}`,
        '',
        summaryText,
      ];
      const meta: string[] = [];
      if (repoName) {
        meta.push(`- **Référentiel analysé :** ${repoName}`);
      }
      meta.push(`- **Résultats :** ${nodes.length} noeuds analysés, ${links.length} relations évaluées.`);
      summaryLines.push('', ...meta);

      const summaryMessage = summaryLines.filter(Boolean).join('\n');

      appendAssistantMessage(summaryMessage, { markdown: true });

      if (traceLines.length) {
        appendAssistantMessage('', { details: traceLines });
      }

      onScenarioResult?.({
        title: payload.scenario_name,
        summary: payload.answer,
        nodes,
        links,
        trace: traceLines,
        repo: repoName,
        graph_steps: payload.graph_steps || undefined,
      });
    } catch (error) {
      console.error('Scenario error:', error);
      appendAssistantMessage('Scenario execution is temporarily unavailable. Please try again in a moment.');
      onScenarioResult?.(null);
    }
  };

  const handleSendMessage = async () => {
    const trimmedInput = inputValue.trim();
    if (!trimmedInput) return;

    const requiresAgent = mode === 'ask' || mode === 'agent-auto';
    if (requiresAgent && !selectedAgent) {
      appendAssistantMessage("Sélectionnez d'abord un agent avant d'utiliser ce mode.");
      return;
    }

    const userMessage = makeMessage('user', inputValue);
    setMessages(prev => [...prev, userMessage]);
    setInputValue('');
    setIsLoading(true);
    onScenarioResult?.(null);

    try {

      if (mode === 'ask') {
        const response = await fetch(`${apiBaseUrl}/api/agent/chat`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({
            message: trimmedInput,
            graph_id: selectedAgent,
          }),
        });

        if (!response.ok) {
          throw new Error('Failed to get response from agent');
        }

        const data = await response.json();
        const displayContent = (data.response || '').trim();

        if (displayContent) {
          appendAssistantMessage(displayContent);
        }

        onScenarioResult?.(null);
      } else if (mode === 'agent-auto') {
        const kgForQuery = selectedAgent ? (agentKgMap[selectedAgent] ?? 'grape_unified') : 'grape_unified';
        await executeScenario(trimmedInput, kgForQuery);
      } else {
        const config = MODE_CONFIG[mode];
        const demoId = config.demoId;
        if (!demoId) {
          throw new Error('Demo mode mal configuré.');
        }
        const kgForQuery = config.kg || (selectedAgent ? agentKgMap[selectedAgent] : 'grape_unified');
        await executeScenario(trimmedInput, kgForQuery, null, demoId);
      }
    } catch (error) {
      console.error('Error calling agent:', error);
      appendAssistantMessage('An unexpected error occurred while contacting the agent. Please try again.');
      onScenarioResult?.(null);
    } finally {
      setIsLoading(false);
    }
  };

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSendMessage();
    }
  };

  return (
    <div className="flex h-full flex-col">
      {/* Chat Header */}
      <div className="px-6 pb-3">
        <h3 className="text-lg font-semibold text-[#1C1C1C]">
          Conversation
        </h3>
        <p className="text-sm text-[#6B7280] mt-1">
          Current mode: {currentModeConfig.label}
        </p>
      </div>

      {/* Messages Area */}
      <div className="flex-1 overflow-y-auto px-6 pb-6 space-y-4">
        {messages.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-full text-center">
            <div className="mb-4">
              <svg
                className="w-16 h-16 text-[#E57373] mx-auto"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={1.5}
                  d="M8 10h.01M12 10h.01M16 10h.01M9 16H5a2 2 0 01-2-2V6a2 2 0 012-2h14a2 2 0 012 2v8a2 2 0 01-2 2h-5l-5 5v-5z"
                />
              </svg>
            </div>
            <h4 className="text-lg font-semibold text-[#1C1C1C] mb-2">
              Commencez l’analyse
            </h4>
            <p className="text-[#6B7280] max-w-md">
              Choisissez un mode ci-dessous, puis saisissez votre question pour lancer le raisonnement.
            </p>
          </div>
        ) : (
          <>
            {messages.map((message) => (
              <div
                key={message.id}
                className={`flex ${message.role === 'user' ? 'justify-end' : 'justify-start'}`}
              >
                <div
                  className={`max-w-[80%] text-sm leading-relaxed ${
                    message.role === 'user' ? 'text-[#1C1C1C] text-right' : 'text-[#1C1C1C]'
                  }`}
                >
                  {message.role === 'assistant' && message.markdown ? (
                    <ReactMarkdown className="text-[#1C1C1C] text-sm leading-relaxed space-y-2 [&_ul]:list-disc [&_ul]:pl-5 [&_ol]:list-decimal [&_ol]:pl-5 [&_code]:font-mono [&_strong]:text-[#1C1C1C]">
                      {message.content}
                    </ReactMarkdown>
                  ) : (
                    message.content && (
                      <div className="whitespace-pre-wrap break-words">
                        {message.content}
                      </div>
                    )
                  )}
                  {message.details && message.details.length > 0 && (
                    <details className="mt-2 rounded-md border border-[#E5E7EB] bg-[#F9FAFB] px-3 py-2 text-xs text-[#4B5563]">
                      <summary className="cursor-pointer text-[#E57373] font-medium">
                        Reasoning Steps
                      </summary>
                      <ul className="mt-2 space-y-1 list-disc pl-4">
                        {message.details.map((line, index) => (
                          <li key={index}>{line}</li>
                        ))}
                      </ul>
                    </details>
                  )}
                  <div className={`text-xs mt-1 text-[#9CA3AF] ${message.role === 'user' ? '' : ''}`}>
                    {message.timestamp.toLocaleTimeString([], {
                      hour: '2-digit',
                      minute: '2-digit',
                    })}
                  </div>
                </div>
              </div>
            ))}
            {isLoading && (
              <div className="flex justify-start">
                <div className="px-2 py-1">
                  <div className="flex space-x-2">
                    <div className="w-2 h-2 bg-[#6B7280] rounded-full animate-bounce" style={{ animationDelay: '0ms' }} />
                    <div className="w-2 h-2 bg-[#6B7280] rounded-full animate-bounce" style={{ animationDelay: '150ms' }} />
                    <div className="w-2 h-2 bg-[#6B7280] rounded-full animate-bounce" style={{ animationDelay: '300ms' }} />
                  </div>
                </div>
              </div>
            )}
            <div ref={messagesEndRef} />
          </>
        )}
      </div>

      {/* Input Area */}
      <div className="px-6 pt-4">
        <div className="flex flex-col gap-2 mb-4">
          <div className="relative" ref={modeMenuRef}>
            <button
              type="button"
              onClick={() => setModeMenuOpen(prev => !prev)}
              className="flex w-full items-center justify-between rounded-lg border border-[#E5E7EB] bg-white px-4 py-2 text-xs font-medium text-[#1C1C1C] hover:border-[#E57373] hover:text-[#E57373] transition-colors"
            >
              <span>Mode : {currentModeConfig.label}</span>
              <span className={`transition-transform ${modeMenuOpen ? 'rotate-180' : ''}`}>
                ▾
              </span>
            </button>
            {modeMenuOpen && (
              <div className="absolute z-50 mt-2 w-72 rounded-lg border border-[#E5E7EB] bg-white shadow-lg">
                <button
                  type="button"
                  onClick={() => applyMode('ask')}
                  className="block w-full px-4 py-3 text-left text-sm text-[#1C1C1C] hover:bg-[#FEF3F3]"
                >
                  Ask (LLM only)
                </button>
                <div className="border-t border-[#F3F4F6]" />
                <div className="px-4 py-2 text-xs font-semibold uppercase text-[#9CA3AF] flex items-center justify-between">
                  <span>Agent</span>
                  <span className="text-[#D1D5DB]">▸</span>
                </div>
                <button
                  type="button"
                  onClick={() => applyMode('agent-auto')}
                  className="block w-full px-6 py-2 text-left text-sm text-[#1C1C1C] hover:bg-[#FEF3F3]"
                >
                  Auto Scenario
                </button>
                <button
                  type="button"
                  onClick={() => applyMode('demo-s1')}
                  className="block w-full px-6 py-2 text-left text-sm text-[#1C1C1C] hover:bg-[#FEF3F3]"
                >
                  Patient Explorer (S1)
                </button>
                <button
                  type="button"
                  onClick={() => applyMode('demo-s2')}
                  className="block w-full px-6 py-2 text-left text-sm text-[#1C1C1C] hover:bg-[#FEF3F3]"
                >
                  Path Finder (S2)
                </button>
                <button
                  type="button"
                  onClick={() => applyMode('demo-s3')}
                  className="block w-full px-6 py-2 text-left text-sm text-[#1C1C1C] hover:bg-[#FEF3F3]"
                >
                  Risk Verificator (S3)
                </button>
                <div className="border-t border-[#F3F4F6]" />
                <button
                  type="button"
                  onClick={() => applyMode('deep')}
                  className="block w-full px-4 py-3 text-left text-sm text-[#1C1C1C] hover:bg-[#FEF3F3]"
                >
                  Deep Reasoning
                </button>
              </div>
            )}
          </div>
          <span className="text-xs text-[#9CA3AF]">
            {currentModeConfig.helper}
          </span>
        </div>
        <div className="flex gap-2">
          <textarea
            value={inputValue}
            onChange={(e) => setInputValue(e.target.value)}
            onKeyPress={handleKeyPress}
            placeholder={textareaPlaceholder}
            disabled={isLoading}
            rows={1}
            className="flex-1 px-4 py-3 text-sm border border-[#E5E7EB] rounded-lg focus:outline-none focus:ring-2 focus:ring-[#E57373] focus:border-transparent placeholder:text-[#6B7280] resize-none disabled:bg-[#F9FAFB] disabled:cursor-not-allowed"
          />
          <button
            onClick={handleSendMessage}
            disabled={isLoading || !inputValue.trim() || (requiresAgent && !selectedAgent)}
            className="px-6 py-3 bg-[#E57373] text-white rounded-lg font-medium hover:bg-[#D55555] transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
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
                d="M12 19l9 2-9-18-9 18 9-2zm0 0v-8"
              />
            </svg>
            Send
          </button>
        </div>
        <p className="text-xs text-[#6B7280] mt-2">
          Press Enter to send, Shift + Enter for new line
        </p>
      </div>
    </div>
  );
}
