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
}

interface ChatInterfaceProps {
  selectedAgent: string | null;
  onScenarioResult?: (data: ScenarioResultData | null) => void;
}

const agentKgMap: Record<string, string> = {
  'hearing-tinnitus': 'grape_hearing',
  'psychiatry-depression': 'grape_psychiatry',
  'integrative-health': 'grape_unified',
};

const repoFromKg = (kgName: string | null | undefined) => {
  if (!kgName) return null;
  return kgName.startsWith('grape_') ? kgName.replace('grape_', '') : kgName;
};

const scenarioProgressMap: Record<string, string[]> = {
  scenario_1_neighbourhood: [
    'Step 1 – Identifying semantic entry points in the question…',
    'Step 2 – Generating a targeted SPARQL query…',
    'Step 3 – Interpreting graph results and compiling the answer…',
  ],
  scenario_2_multihop: [
    'Step 1 – Anchoring the source and target concepts across domains…',
    'Step 2 – Exploring multi-hop relational paths in the unified graph…',
    'Step 3 – Analysing discovered paths and assembling the explanation…',
  ],
  scenario_3_federation: [
    'Step 1 – Scanning hearing and psychiatry graphs for alignable concepts…',
    'Step 2 – Retrieving cross-graph correspondences via owl:sameAs links…',
    'Step 3 – Consolidating aligned concepts into an interpretable summary…',
  ],
  scenario_4_validation: [
    'Step 1 – Formalising the assertion to validate…',
    'Step 2 – Checking available graph evidence for the claim…',
    'Step 3 – Summarising the conclusion and supporting triples…',
  ],
};

type ShortcutConfig = {
  id: string;
  label: string;
  question: string;
  scenarioId: string | null;
  kg?: string | null;
};

const scenarioShortcuts: ShortcutConfig[] = [
  {
    id: 'auto',
    label: 'Auto',
    question: '',
    scenarioId: null,
    kg: null,
  },
  {
    id: 'scenario_1_neighbourhood',
    label: 'Scénario 1',
    question: 'Pour ce patient suivi pour acouphènes (tinnitus) persistants, quels symptômes associés ou facteurs aggravants dois-je explorer en priorité ?',
    scenarioId: 'scenario_1_neighbourhood',
    kg: 'grape_hearing',
  },
  {
    id: 'scenario_2_multihop',
    label: 'Scénario 2',
    question: 'Chez cette patiente atteinte de stress chronique (Chronic Stress) qui commence à perdre l’audition (Hearing Loss), quels enchaînements cliniques expliquent la progression ?',
    scenarioId: 'scenario_2_multihop',
    kg: 'grape_unified',
  },
  {
    id: 'scenario_3_federation',
    label: 'Scénario 3',
    question: 'Existe-t-il des correspondances documentées entre Tinnitus et Generalized Anxiety Disorder qui appuieraient une prise en charge conjointe ?',
    scenarioId: 'scenario_3_federation',
    kg: 'grape_unified',
  },
  {
    id: 'scenario_4_validation',
    label: 'Scénario 4',
    question: 'Peux-tu confirmer si la thérapie cognitivo-comportementale (CBT) est bien enregistrée comme traitement de la perte auditive (Hearing Loss) et citer les alternatives présentes ?',
    scenarioId: 'scenario_4_validation',
    kg: 'grape_unified',
  },
];

export default function ChatInterface({ selectedAgent, onScenarioResult }: ChatInterfaceProps) {
  const apiBaseUrl = process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:8000';
  const [messages, setMessages] = useState<Message[]>([]);
  const [inputValue, setInputValue] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [forcedScenarioId, setForcedScenarioId] = useState<string | null>(null);
  const [forcedKg, setForcedKg] = useState<string | null>(null);
  const [forcedQuestion, setForcedQuestion] = useState<string | null>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);

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

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

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

      const introMessage = scenarioIdOverride
        ? `Scenario ${payload.scenario_name} lancé manuellement. Initialisation du pipeline…`
        : `Scenario detected (${payload.scenario_name}). Initialising analysis pipeline…`;

      appendAssistantMessage(introMessage);
      for (const step of progressSteps) {
        await wait(300);
        appendAssistantMessage(step);
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

      const summaryLines = [
        `## ${payload.scenario_name}`,
        '',
        payload.answer || '',
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
      });
    } catch (error) {
      console.error('Scenario error:', error);
      appendAssistantMessage('Scenario execution is temporarily unavailable. Please try again in a moment.');
      onScenarioResult?.(null);
    }
  };

  const handleSendMessage = async () => {
    if (!inputValue.trim() || !selectedAgent) return;

    const userMessage = makeMessage('user', inputValue);
    setMessages(prev => [...prev, userMessage]);
    const currentInput = inputValue;
    const trimmedInput = currentInput.trim();
    setInputValue('');
    setIsLoading(true);
    onScenarioResult?.(null);

    try {
      if (forcedScenarioId) {
        const kgForQuery = forcedKg || (selectedAgent ? agentKgMap[selectedAgent] : 'grape_unified');
        const matchesDemo = Boolean(forcedQuestion && forcedQuestion.trim() === trimmedInput);
        const demoId = matchesDemo ? forcedScenarioId : null;
        await executeScenario(currentInput, kgForQuery, forcedScenarioId, demoId);
      } else {
        const response = await fetch(`${apiBaseUrl}/api/agent/chat`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({
            message: currentInput,
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

        if (data.is_query) {
          const kgForQuery = data.suggested_kg || (selectedAgent ? agentKgMap[selectedAgent] : 'grape_unified');
          await executeScenario(currentInput, kgForQuery);
        } else {
          onScenarioResult?.(null);
        }
      }
    } catch (error) {
      console.error('Error calling agent:', error);
      appendAssistantMessage('An unexpected error occurred while contacting the agent. Please try again.');
      onScenarioResult?.(null);
    } finally {
      setIsLoading(false);
      setForcedScenarioId(null);
      setForcedKg(null);
      setForcedQuestion(null);
    }
  };

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSendMessage();
    }
  };

  const handleShortcut = (shortcut: ShortcutConfig) => {
    if (shortcut.id === 'auto') {
      setForcedScenarioId(null);
      setForcedKg(null);
      setForcedQuestion(null);
      setInputValue('');
      appendAssistantMessage('Mode auto activé : posez votre question, je sélectionnerai automatiquement le scénario adapté.');
      onScenarioResult?.(null);
      return;
    }

    setInputValue(shortcut.question);
    setForcedScenarioId(shortcut.scenarioId);
    setForcedKg(shortcut.kg ?? null);
    setForcedQuestion(shortcut.question);
    onScenarioResult?.(null);
  };

  return (
    <div className="flex h-full flex-col">
      {/* Chat Header */}
      <div className="px-6 pb-3">
        <h3 className="text-lg font-semibold text-[#1C1C1C]">
          Conversation
        </h3>
        <p className="text-sm text-[#6B7280] mt-1">
          {selectedAgent
            ? 'Chat with your selected agent about the knowledge graph'
            : 'Please select an agent to start chatting'
          }
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
              Start a Conversation
            </h4>
            <p className="text-[#6B7280] max-w-md">
              {selectedAgent
                ? 'Type a message below to start chatting with your agent'
                : 'Select an agent from the dropdown to begin'
              }
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
                        Détails de l’orchestration
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
        <div className="flex flex-wrap items-center gap-2 mb-3">
          {scenarioShortcuts.map(shortcut => (
            <button
              key={shortcut.id}
              onClick={() => handleShortcut(shortcut)}
              className="rounded-full border border-[#E5E7EB] px-4 py-2 text-xs font-medium text-[#6B7280] hover:border-[#E57373] hover:text-[#E57373] transition-colors"
              type="button"
            >
              {shortcut.label}
            </button>
          ))}
          <span className="text-xs text-[#9CA3AF]">
            Préremplir une question démo, puis personnalisez avant envoi.
          </span>
        </div>
        <div className="flex gap-2">
          <textarea
            value={inputValue}
            onChange={(e) => setInputValue(e.target.value)}
            onKeyPress={handleKeyPress}
            placeholder={selectedAgent ? "Type your message..." : "Select an agent first..."}
            disabled={!selectedAgent || isLoading}
            rows={1}
            className="flex-1 px-4 py-3 text-sm border border-[#E5E7EB] rounded-lg focus:outline-none focus:ring-2 focus:ring-[#E57373] focus:border-transparent placeholder:text-[#6B7280] resize-none disabled:bg-[#F9FAFB] disabled:cursor-not-allowed"
          />
          <button
            onClick={handleSendMessage}
            disabled={!selectedAgent || !inputValue.trim() || isLoading}
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
