import type {
  DemoNotification,
  LabInsight,
  MedicalRecord,
  NavItem,
  NavSection,
  PrescriptionItem,
  SummaryCard,
  TimelineEvent,
} from "../types";

export const productName = "Personal Health Copilot";

export const demoBanner =
  "All figures on this screen are synthetic demo content for the byteXL HacXLerate 2026 prototype. They are not real patient records.";

export const demoProfile = {
  initials: "AL",
  displayName: "Alex Rivera (demo)",
  role: "Demo participant",
};

export const navItems: NavItem[] = [
  { id: "overview", label: "Overview" },
  { id: "health-ai", label: "Health AI" },
  { id: "records", label: "Medical Records" },
  { id: "labs", label: "Lab Results" },
  { id: "prescriptions", label: "Prescriptions" },
  { id: "timeline", label: "Health Timeline" },
  { id: "settings", label: "Settings" },
];

export const summaryCards: SummaryCard[] = [
  {
    id: "records",
    label: "Medical Records",
    value: "8 sample files",
    detail: "Synthetic uploads for layout review",
    icon: "folder",
  },
  {
    id: "labs",
    label: "Lab Reports",
    value: "3 sample panels",
    detail: "Illustrative values only",
    icon: "flask",
  },
  {
    id: "prescriptions",
    label: "Prescriptions",
    value: "4 sample entries",
    detail: "Not real medications or orders",
    icon: "pill",
  },
  {
    id: "followups",
    label: "Upcoming Follow-ups",
    value: "2 sample visits",
    detail: "Placeholder calendar items",
    icon: "calendar",
  },
];

export const medicalRecords: MedicalRecord[] = [
  {
    id: "rec-001",
    name: "Annual physical — sample CBC panel.pdf",
    type: "Lab report",
    uploadedOn: "12 Mar 2026",
    status: "Ready to review (demo)",
    sourceNote: "Synthetic lab PDF used to demonstrate the records table.",
    origin: "demo",
  },
  {
    id: "rec-002",
    name: "Primary care visit note — sample.docx",
    type: "Visit note",
    uploadedOn: "04 Mar 2026",
    status: "Listed (demo)",
    sourceNote: "Placeholder visit note. No extraction has been performed.",
    origin: "demo",
  },
  {
    id: "rec-003",
    name: "Chest X-ray summary — sample.pdf",
    type: "Imaging summary",
    uploadedOn: "18 Feb 2026",
    status: "Queued (demo)",
    sourceNote: "Queued is a UI state only. Files are not processed in this milestone.",
    origin: "demo",
  },
  {
    id: "rec-004",
    name: "Medication list — sample clinic.pdf",
    type: "Prescription",
    uploadedOn: "11 Feb 2026",
    status: "Listed (demo)",
    sourceNote: "Sample medication list for the prescriptions preview.",
    origin: "demo",
  },
  {
    id: "rec-005",
    name: "Metabolic panel — sample.pdf",
    type: "Lab report",
    uploadedOn: "29 Jan 2026",
    status: "Ready to review (demo)",
    sourceNote: "Illustrative chemistry panel for the dashboard cards.",
    origin: "demo",
  },
  {
    id: "rec-006",
    name: "Discharge summary — sample encounter.pdf",
    type: "Discharge summary",
    uploadedOn: "09 Jan 2026",
    status: "Listed (demo)",
    sourceNote: "Synthetic discharge packet. Not linked to a real admission.",
    origin: "demo",
  },
  {
    id: "rec-007",
    name: "Lipid panel — sample.pdf",
    type: "Lab report",
    uploadedOn: "02 Dec 2025",
    status: "Ready to review (demo)",
    sourceNote: "Sample lipid values for educational copy in later milestones.",
    origin: "demo",
  },
  {
    id: "rec-008",
    name: "Dermatology follow-up note — sample.pdf",
    type: "Visit note",
    uploadedOn: "15 Nov 2025",
    status: "Queued (demo)",
    sourceNote: "Placeholder specialty note used in the timeline preview.",
    origin: "demo",
  },
];

export const labInsight: LabInsight = {
  panelName: "Sample complete blood count",
  testName: "Hemoglobin",
  value: "13.8",
  unit: "g/dL",
  sampleReferenceRange: "12.0–16.0 g/dL (illustrative adult range, not personalized)",
  statusLabel: "Within the listed sample range",
  educationalNote:
    "Hemoglobin is a protein in red blood cells that carries oxygen. Laboratories publish reference intervals to help clinicians interpret a result in context. This example is fictional, is not a diagnosis, and is not medical advice. Always review actual results with a licensed clinician.",
};

export const timelineEvents: TimelineEvent[] = [
  {
    id: "tl-001",
    date: "12 Mar 2026",
    title: "Sample CBC panel added",
    documentType: "Lab report",
    summary: "Synthetic laboratory PDF listed for the dashboard preview.",
  },
  {
    id: "tl-002",
    date: "04 Mar 2026",
    title: "Sample primary care visit",
    documentType: "Visit note",
    summary: "Placeholder encounter note. No clinical extraction ran.",
  },
  {
    id: "tl-003",
    date: "18 Feb 2026",
    title: "Sample imaging summary",
    documentType: "Imaging summary",
    summary: "Illustrative radiology text used to fill the timeline.",
  },
  {
    id: "tl-004",
    date: "11 Feb 2026",
    title: "Sample medication list",
    documentType: "Prescription",
    summary: "Demo prescription file. Not a real pharmacy order.",
  },
  {
    id: "tl-005",
    date: "09 Jan 2026",
    title: "Sample discharge packet",
    documentType: "Discharge summary",
    summary: "Synthetic hospital paperwork for chronology only.",
  },
];

export const prescriptions: PrescriptionItem[] = [
  {
    id: "rx-001",
    name: "Sample medication A",
    sampleSig: "Example directions for layout only",
    clinic: "Northridge Sample Clinic",
    listedOn: "11 Feb 2026",
  },
  {
    id: "rx-002",
    name: "Sample medication B",
    sampleSig: "Example directions for layout only",
    clinic: "Northridge Sample Clinic",
    listedOn: "11 Feb 2026",
  },
  {
    id: "rx-003",
    name: "Sample inhaler (demo)",
    sampleSig: "Example directions for layout only",
    clinic: "Riverside Demo Pharmacy",
    listedOn: "02 Dec 2025",
  },
  {
    id: "rx-004",
    name: "Sample vitamin listing",
    sampleSig: "Example directions for layout only",
    clinic: "Riverside Demo Pharmacy",
    listedOn: "15 Nov 2025",
  },
];

export const demoNotifications: DemoNotification[] = [
  {
    id: "n-001",
    title: "Upload is not connected yet",
    body: "File intake, OCR, and AI extraction are planned for later milestones.",
    time: "Today",
  },
  {
    id: "n-002",
    title: "Demo records loaded",
    body: "The dashboard is showing synthetic files so the interface can be reviewed.",
    time: "Today",
  },
];

export const pageCopy: Record<NavSection, { title: string; description: string }> = {
  overview: {
    title: "Overview",
    description: "A calm snapshot of sample records, labs, and timeline items.",
  },
  "health-ai": {
    title: "Health AI Copilot",
    description: "Conversational health assistant grounded in your verified medical records with citations.",
  },
  records: {
    title: "Medical Records",
    description: "Browse the synthetic document list used to design this screen.",
  },
  labs: {
    title: "Lab Results",
    description: "Preview how a sample laboratory value will be explained in plain language.",
  },
  prescriptions: {
    title: "Prescriptions",
    description: "Placeholder medication entries. These are not real prescriptions.",
  },
  timeline: {
    title: "Health Timeline",
    description: "A chronological view of the same synthetic events shown on Overview.",
  },
  settings: {
    title: "Settings",
    description: "Prototype preferences. No account or health data is stored yet.",
  },
};
