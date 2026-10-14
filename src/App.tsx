import { useCallback, useEffect, useState } from "react";
import {
  LabsPage,
  PrescriptionsPage,
  RecordsPage,
  SettingsPage,
  TimelinePage,
} from "./components/dashboard/SectionPages";
import { OverviewPage } from "./components/dashboard/OverviewPage";
import { HealthAiPage } from "./components/dashboard/HealthAiPage";
import {
  UploadRecordDialog,
  type SelectedUpload,
} from "./components/dashboard/UploadRecordDialog";
import { AppShell } from "./components/layout/AppShell";
import { medicalRecords } from "./data/demoData";
import { useBoolean } from "./hooks/useBoolean";
import {
  fetchPatients,
  fetchSavedDocuments,
} from "./lib/persistenceApi";
import { createSessionRecord } from "./lib/records";
import { filterRecords } from "./lib/utils";
import type {
  DocumentType,
  MedicalRecord,
  NavSection,
  PatientRecord,
  SavedMedicalDocument,
} from "./types";

function toMedicalRecord(doc: SavedMedicalDocument): MedicalRecord {
  return {
    id: `db-${doc.id}`,
    name: doc.filename,
    type: (doc.document_type as DocumentType) || "Other",
    uploadedOn: doc.upload_date || doc.created_at.slice(0, 10),
    status: "Saved in Database",
    sourceNote: `Persisted in PostgreSQL database with verified clinical extractions (${doc.diagnoses_count} diagnoses, ${doc.medications_count} medicines, ${doc.lab_results_count} lab tests).`,
    origin: "database",
    fileSizeLabel: `${doc.total_char_count} chars`,
    persistedDoc: doc,
    persistedId: doc.id,
  };
}

export default function App() {
  const [section, setSection] = useState<NavSection>("overview");
  const [searchQuery, setSearchQuery] = useState("");
  const [records, setRecords] = useState<MedicalRecord[]>(medicalRecords);
  const [currentPatient, setCurrentPatient] = useState<PatientRecord | null>(null);
  const mobileNav = useBoolean(false);
  const uploadDialog = useBoolean(false);

  // Load patient profile and persisted documents on initial mount
  const loadDatabaseRecords = useCallback(async () => {
    try {
      // 1. Fetch patients
      const patients = await fetchPatients();
      if (patients && patients.length > 0) {
        setCurrentPatient(patients[0]);
      }

      // 2. Fetch saved documents
      const docs = await fetchSavedDocuments();
      if (docs) {
        const dbRecords = docs.map(toMedicalRecord);
        setRecords((prev) => {
          const sessionRecords = prev.filter((r) => r.origin === "session");
          // Merge: session files first, then db records, then demo records
          return [...sessionRecords, ...dbRecords, ...medicalRecords];
        });
      }
    } catch (err) {
      // Graceful fallback if backend server is starting or not yet connected
      console.warn("Backend persistence not reached on mount (will retry on user action):", err);
    }
  }, []);

  useEffect(() => {
    loadDatabaseRecords();
  }, [loadDatabaseRecords]);

  const filteredRecords = filterRecords(records, searchQuery);

  function handleNavigate(next: NavSection) {
    setSection(next);
    mobileNav.off();
  }

  function handleAddDocuments(uploads: SelectedUpload[]) {
    const sessionRecords = uploads.map((upload) =>
      createSessionRecord(upload.file, upload.documentType),
    );
    setRecords((current) => [...sessionRecords, ...current]);
  }

  function handleRecordSaved(recordId: string, savedDoc: SavedMedicalDocument) {
    setRecords((prev) =>
      prev.map((r) => {
        if (r.id === recordId) {
          return {
            ...r,
            origin: "database",
            status: "Saved in Database",
            persistedDoc: savedDoc,
            persistedId: savedDoc.id,
            sourceNote: `Persisted in PostgreSQL database (${savedDoc.diagnoses_count} diagnoses, ${savedDoc.medications_count} medicines, ${savedDoc.lab_results_count} lab tests).`,
          };
        }
        return r;
      }),
    );
  }

  function handleRecordDeleted(recordId: string, docId: string) {
    setRecords((prev) =>
      prev.filter((r) => r.id !== recordId && r.persistedId !== docId && r.id !== `db-${docId}`),
    );
  }

  function handleRecordUpdated(recordId: string, updatedDoc: SavedMedicalDocument) {
    setRecords((prev) =>
      prev.map((r) => {
        if (r.id === recordId || r.persistedId === updatedDoc.id || r.id === `db-${updatedDoc.id}`) {
          return {
            ...r,
            name: updatedDoc.filename,
            type: (updatedDoc.document_type as DocumentType) || r.type,
            persistedDoc: updatedDoc,
          };
        }
        return r;
      }),
    );
  }

  return (
    <>
      <AppShell
        section={section}
        searchQuery={searchQuery}
        mobileNavOpen={mobileNav.value}
        onNavigate={handleNavigate}
        onSearchChange={setSearchQuery}
        onOpenMobileNav={mobileNav.on}
        onCloseMobileNav={mobileNav.off}
      >
        {section === "overview" ? (
          <OverviewPage
            records={filteredRecords}
            allRecords={records}
            searchQuery={searchQuery}
            currentPatient={currentPatient}
            onUpload={uploadDialog.on}
            onExplore={() => {
              document.getElementById("summary-heading")?.scrollIntoView({
                behavior: "smooth",
                block: "start",
              });
              document.getElementById("main-content")?.focus();
            }}
            onRecordSaved={handleRecordSaved}
            onRecordDeleted={handleRecordDeleted}
            onRecordUpdated={handleRecordUpdated}
            onRefreshRecords={loadDatabaseRecords}
          />
        ) : null}
        {section === "health-ai" ? (
          <HealthAiPage currentPatient={currentPatient} />
        ) : null}
        {section === "records" ? (
          <RecordsPage
            records={filteredRecords}
            searchQuery={searchQuery}
            currentPatient={currentPatient}
            onRecordSaved={handleRecordSaved}
            onRecordDeleted={handleRecordDeleted}
            onRecordUpdated={handleRecordUpdated}
            onRefreshRecords={loadDatabaseRecords}
          />
        ) : null}
        {section === "labs" ? <LabsPage /> : null}
        {section === "prescriptions" ? <PrescriptionsPage /> : null}
        {section === "timeline" ? <TimelinePage /> : null}
        {section === "settings" ? <SettingsPage /> : null}
      </AppShell>
      <UploadRecordDialog
        open={uploadDialog.value}
        onClose={uploadDialog.off}
        onAddDocuments={handleAddDocuments}
      />
    </>
  );
}

