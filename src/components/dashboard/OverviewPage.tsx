import type {
  MedicalRecord,
  PatientRecord,
  SavedMedicalDocument,
} from "../../types";
import { HealthInsightPreview } from "./HealthInsightPreview";
import { HealthTimelinePreview } from "./HealthTimelinePreview";
import { RecentRecords } from "./RecentRecords";
import { SummaryCards } from "./SummaryCards";
import { WelcomeSection } from "./WelcomeSection";

interface OverviewPageProps {
  records: MedicalRecord[];
  allRecords: MedicalRecord[];
  searchQuery: string;
  currentPatient?: PatientRecord | null;
  onUpload: () => void;
  onExplore: () => void;
  onRecordSaved?: (recordId: string, savedDoc: SavedMedicalDocument) => void;
  onRecordDeleted?: (recordId: string, docId: string) => void;
  onRecordUpdated?: (recordId: string, updatedDoc: SavedMedicalDocument) => void;
  onRefreshRecords?: () => void;
}

export function OverviewPage({
  records,
  allRecords,
  searchQuery,
  currentPatient,
  onUpload,
  onExplore,
  onRecordSaved,
  onRecordDeleted,
  onRecordUpdated,
  onRefreshRecords,
}: OverviewPageProps) {
  return (
    <div className="mx-auto flex max-w-6xl flex-col gap-6">
      <WelcomeSection onUpload={onUpload} onExplore={onExplore} />
      <SummaryCards records={allRecords} />
      <div className="grid gap-6 xl:grid-cols-5">
        <div className="xl:col-span-3">
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

        <div className="flex flex-col gap-6 xl:col-span-2">
          <HealthInsightPreview />
          <HealthTimelinePreview limit={4} />
        </div>
      </div>
    </div>
  );
}
