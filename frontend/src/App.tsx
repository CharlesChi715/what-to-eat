import { useState } from "react";

interface UploadReply {
  saved: string;
  size_kb: number;
}

export default function App() {
  const [file, setFile] = useState<File | null>(null);
  const [reply, setReply] = useState("Server reply will appear here.");

  async function upload() {
    if (!file) {
      setReply("Pick a photo first.");
      return;
    }
    const form = new FormData();
    form.append("photo", file);
    setReply("Uploading...");
    try {
      const res = await fetch("/api/upload", { method: "POST", body: form });
      if (!res.ok) {
        setReply(`Server error: HTTP ${res.status}`);
        return;
      }
      const data: UploadReply = await res.json();
      setReply(JSON.stringify(data, null, 2));
    } catch (err) {
      setReply(`Server unreachable: ${(err as Error).message}`);
    }
  }

  return (
    <main>
      <h1>What to Eat — photo upload test</h1>
      <input
        type="file"
        accept="image/*"
        onChange={(e) => setFile(e.target.files?.[0] ?? null)}
      />
      <button onClick={upload}>Upload</button>
      <pre>{reply}</pre>
    </main>
  );
}
