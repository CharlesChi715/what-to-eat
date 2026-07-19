import { useState } from "react";

interface UploadReply {
  saved: string;
  size_kb: number;
  sent_image: {
    url: string;
    mime_type: string;
    size_kb: number;
  };
  recognition: {
    model: string;
    text: string;
  };
}

export default function App() {
  const [file, setFile] = useState<File | null>(null);
  const [reply, setReply] = useState("Server reply will appear here.");
  const [sentImageUrl, setSentImageUrl] = useState<string | null>(null);

  async function upload() {
    if (!file) {
      setReply("Pick a photo first.");
      return;
    }
    const form = new FormData();
    form.append("photo", file);
    setReply("Uploading...");
    setSentImageUrl(null);
    try {
      const res = await fetch("/api/upload", { method: "POST", body: form });
      if (!res.ok) {
        const error = await res.json().catch(() => null);
        setReply(error?.detail ?? `Server error: HTTP ${res.status}`);
        return;
      }
      const data: UploadReply = await res.json();
      console.log("Upload reply:", data);
      setSentImageUrl(data.sent_image.url);
      setReply(data.recognition.text);
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
        onChange={(e) => {
          setFile(e.target.files?.[0] ?? null);
          setSentImageUrl(null);
        }}
      />
      <button onClick={upload}>Upload</button>
      {sentImageUrl && (
        <section>
          <h2>Image sent to GPT</h2>
          <img className="sent-image" src={sentImageUrl} alt="Image sent to GPT" />
        </section>
      )}
      <pre>{reply}</pre>
    </main>
  );
}
