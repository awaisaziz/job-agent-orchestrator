import { SearchWorkspace } from "../../components/SearchWorkspace";

export default async function SearchPage({
  searchParams,
}: {
  searchParams: Promise<{ searchId?: string }>;
}) {
  const params = await searchParams;
  const rawSearchId = params.searchId;
  const searchId = rawSearchId ? Number(rawSearchId) : NaN;

  if (!Number.isFinite(searchId) || searchId <= 0) {
    return (
      <main className="page-shell">
        <div className="notice notice-error">Missing or invalid search id. Start from the landing page.</div>
      </main>
    );
  }

  return <SearchWorkspace searchId={searchId} />;
}
