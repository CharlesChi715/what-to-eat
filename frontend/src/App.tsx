import { useRef, useState } from "react";

interface RecognizedItem {
  name: string;
  location: string;
  certainty: "certain" | "uncertain";
  alternative_guesses: string[];
  bounding_box: {
    x_min: number;
    y_min: number;
    x_max: number;
    y_max: number;
  };
  thumbnail_url: string;
}

interface FollowUpPhoto {
  area: string;
  reason: string;
}

interface Recognition {
  model: string;
  items: RecognizedItem[];
  follow_up_photos: FollowUpPhoto[];
  no_food_message: string;
}

interface UploadReply {
  saved: string;
  size_kb: number;
  sent_image: {
    url: string;
    mime_type: string;
    size_kb: number;
  };
  recognition: Recognition;
}

interface Confirmation {
  status: "correcting" | "confirmed";
  value: string;
}

interface ActiveFollowUp {
  index: number;
  area: string;
}

export default function App() {
  const fileInput = useRef<HTMLInputElement>(null);
  const [file, setFile] = useState<File | null>(null);
  const [status, setStatus] = useState("Pick a photo to begin.");
  const [sentImageUrl, setSentImageUrl] = useState<string | null>(null);
  const [recognition, setRecognition] = useState<Recognition | null>(null);
  const [confirmations, setConfirmations] = useState<Record<number, Confirmation>>(
    {},
  );
  const [activeFollowUp, setActiveFollowUp] = useState<ActiveFollowUp | null>(
    null,
  );

  async function upload() {
    if (!file) {
      setStatus(
        activeFollowUp
          ? `Pick a closer photo of ${activeFollowUp.area}.`
          : "Pick a photo first.",
      );
      return;
    }

    const form = new FormData();
    form.append("photo", file);
    if (activeFollowUp) {
      form.append("focus_hint", activeFollowUp.area);
    }

    setStatus(activeFollowUp ? "Checking the closer photo…" : "Recognizing food…");
    setSentImageUrl(null);
    try {
      const res = await fetch("/api/upload", { method: "POST", body: form });
      if (!res.ok) {
        const error = await res.json().catch(() => null);
        setStatus(error?.detail ?? `Server error: HTTP ${res.status}`);
        return;
      }

      const data: UploadReply = await res.json();
      setSentImageUrl(data.sent_image.url);
      if (activeFollowUp && recognition) {
        setRecognition({
          ...data.recognition,
          items: [...recognition.items, ...data.recognition.items],
          follow_up_photos: [
            ...recognition.follow_up_photos.filter(
              (_, index) => index !== activeFollowUp.index,
            ),
            ...data.recognition.follow_up_photos,
          ],
          no_food_message:
            data.recognition.no_food_message || recognition.no_food_message,
        });
      } else {
        setRecognition(data.recognition);
        setConfirmations({});
      }
      setActiveFollowUp(null);
      setFile(null);
      if (fileInput.current) fileInput.current.value = "";
      setStatus("Review the result below.");
    } catch (err) {
      setStatus(`Server unreachable: ${(err as Error).message}`);
    }
  }

  function requestCloserPhoto(followUp: FollowUpPhoto, index: number) {
    setActiveFollowUp({ index, area: followUp.area });
    setFile(null);
    setStatus(`Take or choose a closer photo of ${followUp.area}.`);
    if (fileInput.current) {
      fileInput.current.value = "";
      fileInput.current.click();
    }
  }

  function confirmItem(index: number, value: string) {
    setConfirmations((current) => ({
      ...current,
      [index]: { status: "confirmed", value },
    }));
  }

  const confirmedCount = Object.values(confirmations).filter(
    (answer) => answer.status === "confirmed",
  ).length;

  return (
    <main>
      <h1>What to Eat</h1>
      <p className="intro">Photograph your food, then confirm what the app sees.</p>

      <section className="upload-panel">
        {activeFollowUp && (
          <p className="focus-note">
            Focus the next photo on <strong>{activeFollowUp.area}</strong>.
          </p>
        )}
        <input
          ref={fileInput}
          type="file"
          accept="image/*,.heic,.heif"
          capture="environment"
          onChange={(event) => {
            setFile(event.target.files?.[0] ?? null);
            setSentImageUrl(null);
            if (!activeFollowUp) {
              setRecognition(null);
              setConfirmations({});
            }
          }}
        />
        <button type="button" onClick={upload} disabled={!file}>
          {activeFollowUp ? "Upload focused photo" : "Recognize food"}
        </button>
        <p className="status" role="status">
          {status}
        </p>
      </section>

      {sentImageUrl && (
        <section>
          <h2>Latest image checked</h2>
          <img className="sent-image" src={sentImageUrl} alt="Image sent to GPT" />
        </section>
      )}

      {recognition && (
        <section className="results" aria-labelledby="results-heading">
          <div className="results-heading">
            <h2 id="results-heading">Confirm the foods</h2>
            {recognition.items.length > 0 && (
              <span>
                {confirmedCount} of {recognition.items.length} confirmed
              </span>
            )}
          </div>

          {recognition.no_food_message && (
            <p className="empty-result">{recognition.no_food_message}</p>
          )}

          {recognition.items.map((item, index) => {
            const answer = confirmations[index];
            return (
              <article className="food-card" key={`${item.location}-${index}`}>
                <div className="food-identification">
                  <img
                    className="food-thumbnail"
                    src={item.thumbnail_url}
                    alt={`Cropped view of ${item.name}`}
                  />
                  <div>
                    <span className={`certainty ${item.certainty}`}>
                      {item.certainty === "uncertain"
                        ? "Best guess"
                        : "Looks clear"}
                    </span>
                    <h3>{item.name}</h3>
                    <p className="location">Location: {item.location}</p>
                    {item.certainty === "uncertain" &&
                      item.alternative_guesses.length > 0 && (
                        <p>Could also be: {item.alternative_guesses.join(", ")}</p>
                      )}
                  </div>
                </div>

                {answer?.status === "confirmed" ? (
                  <div className="confirmed-answer">
                    <strong>Confirmed: {answer.value}</strong>
                    <button
                      type="button"
                      className="secondary"
                      onClick={() =>
                        setConfirmations((current) => ({
                          ...current,
                          [index]: { status: "correcting", value: answer.value },
                        }))
                      }
                    >
                      Change
                    </button>
                  </div>
                ) : answer?.status === "correcting" ? (
                  <form
                    className="correction"
                    onSubmit={(event) => {
                      event.preventDefault();
                      const value = answer.value.trim();
                      if (value) confirmItem(index, value);
                    }}
                  >
                    <label htmlFor={`correction-${index}`}>What is it?</label>
                    <input
                      id={`correction-${index}`}
                      value={answer.value}
                      autoFocus
                      onChange={(event) =>
                        setConfirmations((current) => ({
                          ...current,
                          [index]: {
                            status: "correcting",
                            value: event.target.value,
                          },
                        }))
                      }
                    />
                    <button type="submit">Save correction</button>
                  </form>
                ) : (
                  <div className="actions">
                    <button type="button" onClick={() => confirmItem(index, item.name)}>
                      Confirm {item.name}
                    </button>
                    <button
                      type="button"
                      className="secondary"
                      onClick={() =>
                        setConfirmations((current) => ({
                          ...current,
                          [index]: { status: "correcting", value: "" },
                        }))
                      }
                    >
                      Correct it
                    </button>
                  </div>
                )}
              </article>
            );
          })}

          {recognition.follow_up_photos.length > 0 && (
            <div className="follow-ups">
              <h2>Need a closer look</h2>
              {recognition.follow_up_photos.map((followUp, index) => (
                <article className="follow-up-card" key={`${followUp.area}-${index}`}>
                  <div>
                    <h3>{followUp.area}</h3>
                    <p>{followUp.reason}</p>
                  </div>
                  <button
                    type="button"
                    onClick={() => requestCloserPhoto(followUp, index)}
                  >
                    Take another photo
                  </button>
                </article>
              ))}
            </div>
          )}
        </section>
      )}
    </main>
  );
}
