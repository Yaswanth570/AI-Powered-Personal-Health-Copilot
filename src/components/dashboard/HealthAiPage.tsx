import {
  useCallback,
  useEffect,
  useRef,
  useState,
  type FormEvent,
  type KeyboardEvent,
} from "react";
import {
  AlertCircle,
  ArrowRight,
  Bot,
  ChevronDown,
  ChevronUp,
  Clock,
  ExternalLink,
  FileText,
  FlaskConical,
  MessageSquare,
  Pill,
  Plus,
  RefreshCw,
  Send,
  ShieldAlert,
  Sparkles,
  Stethoscope,
  Trash2,
  User,
} from "lucide-react";
import {
  createConversation,
  deleteConversation,
  fetchConversation,
  fetchConversations,
  sendChatMessage,
} from "../../lib/chatApi";
import type {
  ChatConversationDetail,
  ChatConversationSummary,
  ChatMessage,
  PatientRecord,
} from "../../types";
import { Badge } from "../ui/badge";
import { Button } from "../ui/button";

interface HealthAiPageProps {
  currentPatient: PatientRecord | null;
}

const SUGGESTED_QUICK_QUESTIONS = [
  {
    title: "Current Medications",
    question: "What medications am I currently taking for diabetes?",
    icon: Pill,
  },
  {
    title: "Lab Trends",
    question: "How has my fasting blood sugar changed across my reports?",
    icon: FlaskConical,
  },
  {
    title: "Lab Explanations",
    question: "Explain my latest lab results and any out-of-range flags.",
    icon: Stethoscope,
  },
  {
    title: "Doctor Instructions",
    question: "Are there any dietary or lifestyle instructions documented by my doctor?",
    icon: FileText,
  },
];

const LOCAL_STORAGE_ACTIVE_CONV = "health_copilot_active_conv";

export function HealthAiPage({ currentPatient }: HealthAiPageProps) {
  const [conversations, setConversations] = useState<ChatConversationSummary[]>([]);
  const [activeConversationId, setActiveConversationId] = useState<string | null>(() => {
    return localStorage.getItem(LOCAL_STORAGE_ACTIVE_CONV);
  });
  const [activeConversation, setActiveConversation] = useState<ChatConversationDetail | null>(null);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [suggestedFollowUps, setSuggestedFollowUps] = useState<string[]>([]);

  const [inputQuery, setInputQuery] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [isHistoryLoading, setIsHistoryLoading] = useState(false);
  const [errorBanner, setErrorBanner] = useState<string | null>(null);
  const [lastFailedMessage, setLastFailedMessage] = useState<string | null>(null);

  const [expandedCitations, setExpandedCitations] = useState<Record<string, boolean>>({});
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);

  // Auto-scroll to bottom of messages
  const scrollToBottom = useCallback(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, []);

  useEffect(() => {
    scrollToBottom();
  }, [messages, isLoading, scrollToBottom]);

  // Load patient conversations list
  const loadConversations = useCallback(
    async (preferredConvId?: string | null) => {
      if (!currentPatient?.id) return;
      setIsHistoryLoading(true);
      try {
        const convs = await fetchConversations(currentPatient.id);
        setConversations(convs);

        const targetId = preferredConvId !== undefined ? preferredConvId : activeConversationId;
        const exists = convs.find((c) => c.id === targetId);

        if (exists) {
          setActiveConversationId(exists.id);
          localStorage.setItem(LOCAL_STORAGE_ACTIVE_CONV, exists.id);
          // Load messages
          const detail = await fetchConversation(currentPatient.id, exists.id);
          setActiveConversation(detail);
          setMessages(detail.messages || []);
        } else if (convs.length > 0) {
          const first = convs[0];
          setActiveConversationId(first.id);
          localStorage.setItem(LOCAL_STORAGE_ACTIVE_CONV, first.id);
          const detail = await fetchConversation(currentPatient.id, first.id);
          setActiveConversation(detail);
          setMessages(detail.messages || []);
        } else {
          setActiveConversationId(null);
          setActiveConversation(null);
          setMessages([]);
          localStorage.removeItem(LOCAL_STORAGE_ACTIVE_CONV);
        }
      } catch (err) {
        console.warn("Failed to load conversations:", err);
      } finally {
        setIsHistoryLoading(false);
      }
    },
    [currentPatient, activeConversationId],
  );

  useEffect(() => {
    if (currentPatient?.id) {
      loadConversations();
    }
  }, [currentPatient?.id, loadConversations]);

  // Handle switching conversation
  async function handleSelectConversation(convId: string) {
    if (!currentPatient?.id || convId === activeConversationId) return;
    setErrorBanner(null);
    setActiveConversationId(convId);
    localStorage.setItem(LOCAL_STORAGE_ACTIVE_CONV, convId);
    setIsHistoryLoading(true);
    try {
      const detail = await fetchConversation(currentPatient.id, convId);
      setActiveConversation(detail);
      setMessages(detail.messages || []);
      setSuggestedFollowUps([]);
    } catch (err) {
      setErrorBanner(err instanceof Error ? err.message : "Failed to load consultation.");
    } finally {
      setIsHistoryLoading(false);
    }
  }

  // Handle starting a fresh conversation
  async function handleNewConversation() {
    if (!currentPatient?.id) return;
    setErrorBanner(null);
    setIsLoading(true);
    try {
      const newConv = await createConversation(currentPatient.id, "Health Consultation");
      setActiveConversationId(newConv.id);
      localStorage.setItem(LOCAL_STORAGE_ACTIVE_CONV, newConv.id);
      setActiveConversation(newConv);
      setMessages([]);
      setSuggestedFollowUps([]);
      setConversations((prev) => [
        {
          id: newConv.id,
          patient_id: newConv.patient_id,
          title: newConv.title,
          message_count: 0,
          created_at: newConv.created_at,
          updated_at: newConv.updated_at,
        },
        ...prev,
      ]);
      inputRef.current?.focus();
    } catch (err) {
      setErrorBanner(err instanceof Error ? err.message : "Failed to create new consultation.");
    } finally {
      setIsLoading(false);
    }
  }

  // Handle deleting a conversation
  async function handleDeleteConversation(e: React.MouseEvent, convId: string) {
    e.stopPropagation();
    if (!currentPatient?.id) return;
    if (!window.confirm("Are you sure you want to delete this consultation history?")) return;

    try {
      await deleteConversation(currentPatient.id, convId);
      setConversations((prev) => prev.filter((c) => c.id !== convId));
      if (activeConversationId === convId) {
        const remaining = conversations.filter((c) => c.id !== convId);
        if (remaining.length > 0) {
          handleSelectConversation(remaining[0].id);
        } else {
          setActiveConversationId(null);
          setActiveConversation(null);
          setMessages([]);
          localStorage.removeItem(LOCAL_STORAGE_ACTIVE_CONV);
        }
      }
    } catch (err) {
      setErrorBanner(err instanceof Error ? err.message : "Failed to delete consultation.");
    }
  }

  // Handle sending a message
  async function handleSendMessage(queryText?: string) {
    const textToSend = (queryText !== undefined ? queryText : inputQuery).trim();
    if (!textToSend || !currentPatient?.id || isLoading) return;

    setErrorBanner(null);
    setLastFailedMessage(null);
    setInputQuery("");

    // Optimistically append user message to UI
    const tempUserMessage: ChatMessage = {
      id: `temp-${Date.now()}`,
      conversation_id: activeConversationId || "new",
      role: "user",
      content: textToSend,
      created_at: new Date().toISOString(),
    };
    setMessages((prev) => [...prev, tempUserMessage]);
    setIsLoading(true);

    try {
      const response = await sendChatMessage(
        currentPatient.id,
        activeConversationId,
        textToSend,
      );

      // If a new conversation was created on the backend
      if (!activeConversationId || activeConversationId !== response.conversation_id) {
        setActiveConversationId(response.conversation_id);
        localStorage.setItem(LOCAL_STORAGE_ACTIVE_CONV, response.conversation_id);
      }

      // Replace temp message with confirmed user message and add assistant reply
      setMessages((prev) => {
        const withoutTemp = prev.filter((m) => m.id !== tempUserMessage.id);
        return [...withoutTemp, response.user_message, response.assistant_message];
      });

      setSuggestedFollowUps(response.suggested_follow_ups || []);

      // Refresh conversations list to update title and message count
      loadConversations(response.conversation_id);
    } catch (err) {
      setErrorBanner(
        err instanceof Error
          ? err.message
          : "An unexpected error occurred while communicating with Health Copilot.",
      );
      setLastFailedMessage(textToSend);
      // Remove temporary message on error
      setMessages((prev) => prev.filter((m) => m.id !== tempUserMessage.id));
    } finally {
      setIsLoading(false);
    }
  }

  function handleFormSubmit(e: FormEvent) {
    e.preventDefault();
    handleSendMessage();
  }

  function handleKeyDown(e: KeyboardEvent<HTMLTextAreaElement>) {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSendMessage();
    }
  }

  function toggleCitations(messageId: string) {
    setExpandedCitations((prev) => ({
      ...prev,
      [messageId]: !prev[messageId],
    }));
  }

  // Format assistant markdown with simple paragraphs, bolding, lists, and citations
  function renderMarkdownContent(content: string) {
    const lines = content.split("\n");
    return lines.map((line, idx) => {
      const trimmed = line.trim();
      if (!trimmed) {
        return <div key={idx} className="h-2" />;
      }

      // Bold formatting helper: replace **bold** with <strong>
      const formatBoldAndRefs = (text: string) => {
        const parts = text.split(/(\*\*.*?\*\*|\[Ref:.*?\])/g);
        return parts.map((part, pIdx) => {
          if (part.startsWith("**") && part.endsWith("**")) {
            return (
              <strong key={pIdx} className="font-semibold text-slate-900">
                {part.slice(2, -2)}
              </strong>
            );
          }
          if (part.startsWith("[Ref:") && part.endsWith("]")) {
            return (
              <span
                key={pIdx}
                className="inline-flex items-center px-1.5 py-0.5 mx-0.5 text-xs font-mono font-medium rounded bg-teal-50 text-teal-800 border border-teal-200"
              >
                {part}
              </span>
            );
          }
          return part;
        });
      };

      if (trimmed.startsWith("### ")) {
        return (
          <h4 key={idx} className="text-base font-bold text-slate-900 mt-3 mb-1">
            {formatBoldAndRefs(trimmed.slice(4))}
          </h4>
        );
      }
      if (trimmed.startsWith("## ")) {
        return (
          <h3 key={idx} className="text-lg font-bold text-slate-900 mt-4 mb-1.5">
            {formatBoldAndRefs(trimmed.slice(3))}
          </h3>
        );
      }
      if (trimmed.startsWith("- ") || trimmed.startsWith("* ")) {
        return (
          <li key={idx} className="ml-4 list-disc text-slate-700 my-0.5">
            {formatBoldAndRefs(trimmed.slice(2))}
          </li>
        );
      }
      if (/^\d+\.\s/.test(trimmed)) {
        const numText = trimmed.replace(/^\d+\.\s/, "");
        return (
          <li key={idx} className="ml-4 list-decimal text-slate-700 my-0.5">
            {formatBoldAndRefs(numText)}
          </li>
        );
      }

      return (
        <p key={idx} className="text-slate-700 my-1 leading-relaxed">
          {formatBoldAndRefs(trimmed)}
        </p>
      );
    });
  }

  function getEntityTypeBadge(entityType: string) {
    switch (entityType.toLowerCase()) {
      case "medication":
        return (
          <Badge tone="calm" className="bg-emerald-50 text-emerald-700 border-emerald-200 text-xs">
            <Pill className="h-3 w-3 mr-1" /> Medication
          </Badge>
        );
      case "lab_result":
        return (
          <Badge tone="warn" className="bg-amber-50 text-amber-700 border-amber-200 text-xs">
            <FlaskConical className="h-3 w-3 mr-1" /> Lab Result
          </Badge>
        );
      case "diagnosis":
        return (
          <Badge tone="neutral" className="bg-blue-50 text-blue-700 border-blue-200 text-xs">
            <Stethoscope className="h-3 w-3 mr-1" /> Diagnosis
          </Badge>
        );
      default:
        return (
          <Badge tone="neutral" className="bg-slate-100 text-slate-700 text-xs">
            <FileText className="h-3 w-3 mr-1" /> Document
          </Badge>
        );
    }
  }

  return (
    <div className="flex flex-col h-[calc(100vh-140px)] min-h-[580px] rounded-xl border border-border bg-card shadow-sm overflow-hidden">
      {/* Top Banner: Active Patient & Clinical Grounding Info */}
      <div className="flex flex-wrap items-center justify-between gap-3 px-5 py-3.5 border-b border-border bg-muted/40">
        <div className="flex items-center gap-2.5">
          <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-teal-600 text-white shadow-xs">
            <Sparkles className="h-5 w-5" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h1 className="text-base font-semibold text-foreground">
                Personal Health AI Copilot
              </h1>
              {activeConversation?.title ? (
                <span className="text-xs text-muted-foreground hidden sm:inline">
                  • {activeConversation.title}
                </span>
              ) : null}
              <span className="inline-flex items-center px-2 py-0.5 text-xs font-medium rounded-full bg-teal-50 text-teal-700 border border-teal-200">
                Grounded in Saved Records
              </span>
            </div>
            <p className="text-xs text-muted-foreground">
              {currentPatient ? (
                <>
                  Active Patient: <strong className="font-semibold text-foreground">{currentPatient.display_name}</strong>
                  {currentPatient.age ? ` • Age ${currentPatient.age}` : ""}
                  {currentPatient.gender ? ` • ${currentPatient.gender}` : ""}
                  {currentPatient.document_count ? ` • ${currentPatient.document_count} saved records` : ""}
                </>
              ) : (
                "Connecting to patient records..."
              )}
            </p>
          </div>
        </div>

        <div className="flex items-center gap-2">
          <Button
            variant="outline"
            size="sm"
            onClick={handleNewConversation}
            disabled={isLoading || !currentPatient}
            className="h-8 gap-1.5 text-xs border-teal-200 hover:bg-teal-50 text-teal-800"
          >
            <Plus className="h-3.5 w-3.5 text-teal-600" />
            New Consultation
          </Button>
          <Button
            variant="ghost"
            size="sm"
            onClick={() => loadConversations()}
            disabled={isHistoryLoading || !currentPatient}
            title="Refresh consultations"
            className="h-8 w-8 p-0"
          >
            <RefreshCw className={`h-3.5 w-3.5 ${isHistoryLoading ? "animate-spin" : ""}`} />
          </Button>
        </div>
      </div>

      {/* Main Content: Left Conversation Sidebar + Right Chat Stream */}
      <div className="flex flex-1 overflow-hidden">
        {/* Left Consultation History Sidebar */}
        <aside className="hidden md:flex flex-col w-64 border-r border-border bg-slate-50/50">
          <div className="p-3 border-b border-border flex items-center justify-between text-xs font-semibold text-muted-foreground uppercase tracking-wider">
            <span className="flex items-center gap-1.5">
              <Clock className="h-3.5 w-3.5" /> Consultations ({conversations.length})
            </span>
          </div>

          <div className="flex-1 overflow-y-auto p-2 space-y-1">
            {conversations.length === 0 ? (
              <div className="p-4 text-center text-xs text-muted-foreground italic">
                No past consultations yet. Start a new question to create your first session.
              </div>
            ) : (
              conversations.map((conv) => {
                const isActive = conv.id === activeConversationId;
                return (
                  <div
                    key={conv.id}
                    onClick={() => handleSelectConversation(conv.id)}
                    className={`group relative flex items-start justify-between gap-2 p-2.5 rounded-lg text-xs cursor-pointer transition-all ${
                      isActive
                        ? "bg-teal-50 text-teal-900 border border-teal-200 shadow-2xs font-medium"
                        : "hover:bg-slate-100 text-slate-700"
                    }`}
                  >
                    <div className="flex items-start gap-2 min-w-0">
                      <MessageSquare
                        className={`h-4 w-4 mt-0.5 shrink-0 ${
                          isActive ? "text-teal-600" : "text-muted-foreground"
                        }`}
                      />
                      <div className="truncate">
                        <div className="truncate font-medium">{conv.title}</div>
                        {conv.last_message_preview ? (
                          <p className="truncate text-slate-400 text-[11px] mt-0.5">
                            {conv.last_message_preview}
                          </p>
                        ) : null}
                      </div>
                    </div>

                    <button
                      type="button"
                      onClick={(e) => handleDeleteConversation(e, conv.id)}
                      className="opacity-0 group-hover:opacity-100 p-1 text-slate-400 hover:text-red-600 transition-opacity"
                      title="Delete consultation"
                      aria-label="Delete consultation"
                    >
                      <Trash2 className="h-3.5 w-3.5" />
                    </button>
                  </div>
                );
              })
            )}
          </div>
        </aside>

        {/* Right Chat Stream Container */}
        <section className="flex flex-col flex-1 bg-white overflow-hidden">
          {/* Error Banner */}
          {errorBanner ? (
            <div className="flex items-center justify-between gap-3 px-4 py-2.5 bg-red-50 border-b border-red-200 text-xs text-red-700">
              <div className="flex items-center gap-2">
                <AlertCircle className="h-4 w-4 shrink-0 text-red-600" />
                <span>{errorBanner}</span>
              </div>
              {lastFailedMessage ? (
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => handleSendMessage(lastFailedMessage)}
                  className="h-7 px-2 text-xs border-red-300 hover:bg-red-100 text-red-800"
                >
                  Retry
                </Button>
              ) : (
                <button
                  type="button"
                  onClick={() => setErrorBanner(null)}
                  className="text-red-500 hover:text-red-700 font-bold px-1"
                >
                  ✕
                </button>
              )}
            </div>
          ) : null}

          {/* Chat Messages Scrollable Area */}
          <div className="flex-1 overflow-y-auto p-4 md:p-6 space-y-6">
            {messages.length === 0 ? (
              // Empty State with Suggested Questions
              <div className="max-w-2xl mx-auto py-8 text-center space-y-6">
                <div className="inline-flex h-16 w-16 items-center justify-center rounded-2xl bg-teal-50 border border-teal-100 text-teal-600 shadow-sm">
                  <Bot className="h-8 w-8" />
                </div>

                <div className="space-y-2">
                  <h2 className="text-xl font-bold text-slate-900 font-display">
                    Welcome to your Personal Health AI Copilot
                  </h2>
                  <p className="text-sm text-slate-600 max-w-lg mx-auto">
                    Ask questions about your uploaded prescriptions, laboratory tests, diagnoses,
                    and treatment timelines. Answers are strictly grounded in your verified medical records.
                  </p>
                </div>

                {/* Suggested Questions Grid */}
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 text-left pt-2">
                  {SUGGESTED_QUICK_QUESTIONS.map((item, idx) => {
                    const Icon = item.icon;
                    return (
                      <button
                        key={idx}
                        type="button"
                        onClick={() => handleSendMessage(item.question)}
                        disabled={isLoading || !currentPatient}
                        className="group flex flex-col justify-between p-4 rounded-xl border border-slate-200 bg-white hover:border-teal-300 hover:bg-teal-50/50 hover:shadow-xs transition-all text-left"
                      >
                        <div className="flex items-center gap-2 mb-1.5 text-xs font-semibold text-teal-700">
                          <Icon className="h-4 w-4 text-teal-600 group-hover:scale-110 transition-transform" />
                          <span>{item.title}</span>
                        </div>
                        <p className="text-xs text-slate-700 leading-relaxed group-hover:text-slate-900">
                          "{item.question}"
                        </p>
                      </button>
                    );
                  })}
                </div>
              </div>
            ) : (
              // Message List
              messages.map((msg) => {
                const isUser = msg.role === "user";
                const isExpanded = !!expandedCitations[msg.id];
                const citations = msg.citations || [];

                return (
                  <div
                    key={msg.id}
                    className={`flex items-start gap-3 ${isUser ? "flex-row-reverse" : "flex-row"}`}
                  >
                    {/* Avatar */}
                    <div
                      className={`flex h-8 w-8 shrink-0 items-center justify-center rounded-full shadow-xs ${
                        isUser
                          ? "bg-slate-700 text-white"
                          : "bg-teal-600 text-white ring-2 ring-teal-100"
                      }`}
                    >
                      {isUser ? <User className="h-4 w-4" /> : <Sparkles className="h-4 w-4" />}
                    </div>

                    {/* Bubble */}
                    <div
                      className={`max-w-[85%] sm:max-w-[78%] rounded-2xl px-4 py-3 text-sm shadow-xs ${
                        isUser
                          ? "bg-teal-600 text-white rounded-tr-xs"
                          : "bg-white border border-slate-200 text-slate-800 rounded-tl-xs shadow-[0_1px_3px_rgba(0,0,0,0.04)]"
                      }`}
                    >
                      {/* Message Content */}
                      <div className="prose prose-sm max-w-none">
                        {isUser ? (
                          <p className="whitespace-pre-wrap leading-relaxed">{msg.content}</p>
                        ) : (
                          renderMarkdownContent(msg.content)
                        )}
                      </div>

                      {/* Evidence Citations Section for Assistant Replies */}
                      {!isUser && citations.length > 0 ? (
                        <div className="mt-4 pt-3 border-t border-slate-100">
                          <button
                            type="button"
                            onClick={() => toggleCitations(msg.id)}
                            className="flex items-center gap-1.5 text-xs font-semibold text-teal-700 hover:text-teal-900 transition-colors"
                          >
                            <FileText className="h-3.5 w-3.5 text-teal-600" />
                            <span>
                              Evidence Sources ({citations.length}{" "}
                              {citations.length === 1 ? "reference" : "references"})
                            </span>
                            {isExpanded ? (
                              <ChevronUp className="h-3.5 w-3.5 ml-0.5" />
                            ) : (
                              <ChevronDown className="h-3.5 w-3.5 ml-0.5" />
                            )}
                          </button>

                          {/* Collapsible Citation Details */}
                          {isExpanded ? (
                            <div className="mt-2 space-y-2">
                              {citations.map((cite, cIdx) => (
                                <div
                                  key={cIdx}
                                  className="p-2.5 rounded-lg border border-teal-100 bg-teal-50/40 text-xs text-slate-700 space-y-1"
                                >
                                  <div className="flex flex-wrap items-center justify-between gap-1">
                                    <span className="font-semibold text-slate-900">
                                      {cite.document_name}
                                    </span>
                                    {getEntityTypeBadge(cite.entity_type)}
                                  </div>

                                  {cite.report_date ? (
                                    <div className="text-[11px] text-slate-500">
                                      Date: <span className="font-medium text-slate-700">{cite.report_date}</span>
                                    </div>
                                  ) : null}

                                  <div className="text-slate-800 italic bg-white/70 px-2 py-1 rounded border border-teal-100/60">
                                    “{cite.entity_text}”
                                  </div>

                                  {cite.value ? (
                                    <div className="text-[11px] text-teal-900 font-medium">
                                      Value: {cite.value} {cite.unit || ""}{" "}
                                      {cite.reference_range ? `(Ref: ${cite.reference_range})` : ""}
                                    </div>
                                  ) : null}
                                </div>
                              ))}
                            </div>
                          ) : (
                            /* Collapsed Pill Summary */
                            <div className="mt-2 flex flex-wrap gap-1.5">
                              {citations.map((cite, cIdx) => (
                                <span
                                  key={cIdx}
                                  onClick={() => toggleCitations(msg.id)}
                                  className="inline-flex items-center gap-1 px-2 py-0.5 text-[11px] rounded bg-slate-100 text-slate-700 hover:bg-teal-50 hover:text-teal-800 cursor-pointer transition-colors border border-slate-200"
                                >
                                  <ExternalLink className="h-3 w-3 text-slate-400" />
                                  <span className="font-medium truncate max-w-[140px]">
                                    {cite.document_name}
                                  </span>
                                  {cite.value ? `(${cite.value} ${cite.unit || ""})` : ""}
                                </span>
                              ))}
                            </div>
                          )}
                        </div>
                      ) : null}

                      {/* Timestamp & Model Used */}
                      <div
                        className={`mt-2 flex items-center justify-between text-[10px] ${
                          isUser ? "text-teal-100" : "text-slate-400"
                        }`}
                      >
                        <span>
                          {new Date(msg.created_at).toLocaleTimeString([], {
                            hour: "2-digit",
                            minute: "2-digit",
                          })}
                        </span>
                        {!isUser && msg.model_used ? (
                          <span className="font-mono text-[9px] text-slate-400">
                            {msg.model_used}
                          </span>
                        ) : null}
                      </div>
                    </div>
                  </div>
                );
              })
            )}

            {/* Loading / Thinking Indicator */}
            {isLoading ? (
              <div className="flex items-start gap-3">
                <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-teal-600 text-white shadow-xs">
                  <Sparkles className="h-4 w-4 animate-spin" />
                </div>
                <div className="rounded-2xl rounded-tl-xs px-4 py-3 bg-white border border-slate-200 text-xs text-slate-600 shadow-xs flex items-center gap-2">
                  <div className="flex gap-1">
                    <span className="h-2 w-2 rounded-full bg-teal-500 animate-bounce" />
                    <span
                      className="h-2 w-2 rounded-full bg-teal-500 animate-bounce"
                      style={{ animationDelay: "150ms" }}
                    />
                    <span
                      className="h-2 w-2 rounded-full bg-teal-500 animate-bounce"
                      style={{ animationDelay: "300ms" }}
                    />
                  </div>
                  <span>Grounded clinical synthesis with Gemini...</span>
                </div>
              </div>
            ) : null}

            {/* Contextual Follow-up Suggestions Chips */}
            {!isLoading && suggestedFollowUps.length > 0 ? (
              <div className="pt-2">
                <div className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider mb-2 flex items-center gap-1">
                  <Sparkles className="h-3 w-3 text-teal-600" /> Suggested Follow-ups
                </div>
                <div className="flex flex-wrap gap-2">
                  {suggestedFollowUps.map((suggestion, sIdx) => (
                    <button
                      key={sIdx}
                      type="button"
                      onClick={() => handleSendMessage(suggestion)}
                      className="inline-flex items-center gap-1 px-3 py-1.5 rounded-full text-xs font-medium bg-teal-50 text-teal-800 border border-teal-200 hover:bg-teal-100 hover:border-teal-300 transition-all text-left shadow-2xs"
                    >
                      <span>{suggestion}</span>
                      <ArrowRight className="h-3 w-3 text-teal-600 shrink-0" />
                    </button>
                  ))}
                </div>
              </div>
            ) : null}

            <div ref={messagesEndRef} />
          </div>

          {/* Bottom Chat Input Form & Safety Footer */}
          <div className="border-t border-border bg-slate-50/80 p-3 md:p-4">
            <form onSubmit={handleFormSubmit} className="relative flex items-end gap-2">
              <div className="relative flex-1">
                <textarea
                  ref={inputRef}
                  value={inputQuery}
                  onChange={(e) => setInputQuery(e.target.value)}
                  onKeyDown={handleKeyDown}
                  placeholder={
                    currentPatient
                      ? `Ask a question about ${currentPatient.display_name}'s medical records... (Press Enter to send)`
                      : "Loading patient records..."
                  }
                  rows={2}
                  disabled={isLoading || !currentPatient}
                  className="w-full resize-none rounded-xl border border-slate-300 bg-white p-3 pr-10 text-sm text-slate-900 placeholder:text-slate-400 focus:border-teal-500 focus:outline-none focus:ring-2 focus:ring-teal-500/20 shadow-2xs disabled:bg-slate-100"
                />
              </div>

              <Button
                type="submit"
                disabled={isLoading || !inputQuery.trim() || !currentPatient}
                className="h-11 w-11 shrink-0 rounded-xl bg-teal-600 hover:bg-teal-700 text-white p-0 flex items-center justify-center shadow-xs"
                title="Send question"
                aria-label="Send question"
              >
                <Send className="h-4 w-4" />
              </Button>
            </form>

            {/* Medical Safety & Clinical Guardrails Disclaimer */}
            <div className="mt-2.5 flex items-center justify-center gap-1.5 text-center text-[11px] text-muted-foreground">
              <ShieldAlert className="h-3.5 w-3.5 text-amber-500 shrink-0" />
              <span>
                Personal Health Copilot provides educational explanations strictly based on saved records.
                Always verify with your doctor. Seek emergency care for urgent symptoms.
              </span>
            </div>
          </div>
        </section>
      </div>
    </div>
  );
}
