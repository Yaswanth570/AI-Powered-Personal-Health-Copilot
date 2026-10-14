import { prescriptions } from "../../data/demoData";
import type {
  MedicalRecord,
  PatientRecord,
  SavedMedicalDocument,
} from "../../types";
import { Card, CardDescription, CardHeader, CardTitle } from "../ui/card";
import { HealthInsightPreview } from "./HealthInsightPreview";
import { HealthTimelinePreview } from "./HealthTimelinePreview";
import { RecentRecords } from "./RecentRecords";

interface RecordsPageProps {
  records: MedicalRecord[];
  searchQuery: string;
  currentPatient?: PatientRecord | null;
  onRecordSaved?: (recordId: string, savedDoc: SavedMedicalDocument) => void;
  onRecordDeleted?: (recordId: string, docId: string) => void;
  onRecordUpdated?: (recordId: string, updatedDoc: SavedMedicalDocument) => void;
  onRefreshRecords?: () => void;
}

export function RecordsPage({
  records,
  searchQuery,
  currentPatient,
  onRecordSaved,
  onRecordDeleted,
  onRecordUpdated,
  onRefreshRecords,
}: RecordsPageProps) {
  return (
    <div className="mx-auto max-w-6xl">
      <RecentRecords
        records={records}
        searchQuery={searchQuery}
        currentPatient={currentPatient}
        onRecordSaved={onRecordSaved}
        onRecordDeleted={onRecordDeleted}
        onRecordUpdated={onRecordUpdated}
        onRefreshRecords={onRefreshRecords}
      />
    </div>
  );
}

export function LabsPage() {
  return (
    <div className="mx-auto max-w-3xl">
      <HealthInsightPreview />
    </div>
  );
}

export function PrescriptionsPage() {
  return (
    <div className="mx-auto max-w-4xl">
      <Card>
        <CardHeader>
          <CardTitle>Sample prescriptions</CardTitle>
          <CardDescription>
            These entries are fictional labels for layout. They are not prescriptions, not
            medical advice, and must not be used to take or stop medication.
          </CardDescription>
        </CardHeader>
        <ul className="divide-y divide-border">
          {prescriptions.map((item) => (
            <li key={item.id} className="flex flex-col gap-1 py-4 first:pt-0 sm:flex-row sm:items-center sm:justify-between">
              <div>
                <p className="font-medium text-foreground">{item.name}</p>
                <p className="text-sm text-muted-foreground">{item.sampleSig}</p>
              </div>
              <p className="text-sm text-muted-foreground">
                {item.clinic} · {item.listedOn}
              </p>
            </li>
          ))}
        </ul>
      </Card>
    </div>
  );
}

export function TimelinePage() {
  return (
    <div className="mx-auto max-w-3xl">
      <HealthTimelinePreview />
    </div>
  );
}

export function SettingsPage() {
  return (
    <div className="mx-auto max-w-3xl">
      <Card>
        <CardHeader>
          <CardTitle>System & Storage Settings</CardTitle>
          <CardDescription>
            Step 6 PostgreSQL persistence configuration, clinical AI integration, and patient demo profiles.
          </CardDescription>
        </CardHeader>
        <dl className="grid gap-4 text-sm sm:grid-cols-2 p-4">
          <div className="rounded-md border border-border p-3">
            <dt className="text-xs text-muted-foreground font-medium uppercase tracking-wider">Demo Profile</dt>
            <dd className="mt-1 font-semibold text-foreground">Smt. Sunita Rao (Age 52 / Female)</dd>
            <p className="text-xs text-muted-foreground mt-0.5">Synthetic Indian demo patient for prototype testing</p>
          </div>
          <div className="rounded-md border border-border p-3">
            <dt className="text-xs text-muted-foreground font-medium uppercase tracking-wider">Database Persistence</dt>
            <dd className="mt-1 font-semibold text-foreground">SQLAlchemy 2.x + Alembic</dd>
            <p className="text-xs text-muted-foreground mt-0.5">PostgreSQL / psycopg 3 driver (SQLite fallback)</p>
          </div>
          <div className="rounded-md border border-border p-3">
            <dt className="text-xs text-muted-foreground font-medium uppercase tracking-wider">AI Clinical Model</dt>
            <dd className="mt-1 font-semibold text-foreground">Gemini 3.1 Flash Lite</dd>
            <p className="text-xs text-muted-foreground mt-0.5">Strict clinical extraction with fallback to 3.5</p>
          </div>
          <div className="rounded-md border border-border p-3">
            <dt className="text-xs text-muted-foreground font-medium uppercase tracking-wider">Transactional Safety</dt>
            <dd className="mt-1 font-semibold text-foreground">Atomic DB Commits & Rollbacks</dd>
            <p className="text-xs text-muted-foreground mt-0.5">No partial writes; cascade deletes for linked entities</p>
          </div>
        </dl>
      </Card>
    </div>
  );
}

