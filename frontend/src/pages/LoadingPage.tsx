export default function LoadingPage() {
  return (
    <div className="flex items-center justify-center h-screen">
      <div className="text-center bg-paper-background/60 rounded-lg p-10">
        <div className="animate-spin rounded-full h-12 w-12 border-b-3 border-blue-dark mx-auto mb-4" />
        <p className="text-xl">Loading...</p>
      </div>
    </div>
  );
}
