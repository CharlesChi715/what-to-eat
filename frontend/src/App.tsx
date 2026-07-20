import { useEffect, useRef, useState } from "react";

interface RecognizedItem {
  name: string;
  location: string;
  certainty: "certain" | "uncertain";
  alternative_guesses: string[];
  marker: {
    center_x: number;
    center_y: number;
    radius: number;
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

interface ExpandedImage {
  url: string;
  foodName: string;
}

export default function App() {
  const fileInput = useRef<HTMLInputElement>(null);
  const expandedImageTrigger = useRef<HTMLButtonElement | null>(null);
  const [file, setFile] = useState<File | null>(null);
  const [isUploading, setIsUploading] = useState(false);
  const [status, setStatus] = useState("Pick a photo to begin.");
  const [sentImageUrl, setSentImageUrl] = useState<string | null>(null);
  const [recognition, setRecognition] = useState<Recognition | null>(null);
  const [confirmations, setConfirmations] = useState<Record<number, Confirmation>>(
    {},
  );
  const [activeFollowUp, setActiveFollowUp] = useState<ActiveFollowUp | null>(
    null,
  );
  const [expandedImage, setExpandedImage] = useState<ExpandedImage | null>(null);

  useEffect(() => {
    if (!expandedImage) return;

    const previousOverflow = document.body.style.overflow;
    document.body.style.overflow = "hidden";

    function handleKeyDown(event: KeyboardEvent) {
      if (event.key === "Tab") {
        event.preventDefault();
      }

      if (event.key === "Escape") {
        setExpandedImage(null);
        requestAnimationFrame(() => expandedImageTrigger.current?.focus());
      }
    }

    document.addEventListener("keydown", handleKeyDown);
    return () => {
      document.body.style.overflow = previousOverflow;
      document.removeEventListener("keydown", handleKeyDown);
    };
  }, [expandedImage]);

  function closeExpandedImage() {
    setExpandedImage(null);
    requestAnimationFrame(() => expandedImageTrigger.current?.focus());
  }

  async function upload() {
    if (isUploading) return;

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
    setIsUploading(true);
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
    } finally {
      setIsUploading(false);
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

  function confirmAllCertain() {
    if (!recognition) return;

    setConfirmations((current) => {
      const next = { ...current };

      recognition.items.forEach((item, index) => {
        if (item.certainty === "certain" && current[index] === undefined) {
          next[index] = { status: "confirmed", value: item.name };
        }
      });

      return next;
    });
  }

  const confirmedCount = Object.values(confirmations).filter(
    (answer) => answer.status === "confirmed",
  ).length;
  const unreviewedCertainCount =
    recognition?.items.filter(
      (item, index) =>
        item.certainty === "certain" && confirmations[index] === undefined,
    ).length ?? 0;
  const indexedItems =
    recognition?.items.map((item, index) => ({ item, index })) ?? [];
  const certainItems = indexedItems.filter(
    ({ item }) => item.certainty === "certain",
  );
  const uncertainItems = indexedItems.filter(
    ({ item }) => item.certainty === "uncertain",
  );

  function renderFoodCard(item: RecognizedItem, index: number) {
    const answer = confirmations[index];

    return (
      <article className="food-card" key={`${item.location}-${index}`}>
        <div className="food-identification">
          <button
            type="button"
            className="thumbnail-button"
            aria-label={`Enlarge image of ${item.name}`}
            onClick={(event) => {
              expandedImageTrigger.current = event.currentTarget;
              setExpandedImage({ url: item.thumbnail_url, foodName: item.name });
            }}
          >
            <img
              className="food-thumbnail"
              src={item.thumbnail_url}
              alt={`Full photo with ${item.name} circled in red`}
            />
          </button>
          <div>
            <span className={`certainty ${item.certainty}`}>
              {item.certainty === "uncertain" ? "Best guess" : "Looks clear"}
            </span>
            <h4>{item.name}</h4>
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
  }

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
          id="food-photo"
          ref={fileInput}
          className="file-input"
          type="file"
          accept="image/*,.heic,.heif"
          capture="environment"
          disabled={isUploading}
          onChange={(event) => {
            setFile(event.target.files?.[0] ?? null);
            setSentImageUrl(null);
            if (!activeFollowUp) {
              setRecognition(null);
              setConfirmations({});
            }
          }}
        />
        <label
          className={`file-picker${isUploading ? " disabled" : ""}`}
          htmlFor="food-photo"
          aria-disabled={isUploading}
        >
          <span className="file-picker-action">
            <svg aria-hidden="true" viewBox="0 0 24 24">
              <path d="M8.3 6.5 9.8 4.6h4.4l1.5 1.9H19a2 2 0 0 1 2 2v8.9a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8.5a2 2 0 0 1 2-2h3.3Z" />
              <circle cx="12" cy="13" r="3.5" />
            </svg>
            {file ? "Change photo" : "Choose photo"}
          </span>
          <span
            className={`file-picker-name${file ? " selected" : ""}`}
            title={file?.name}
            aria-live="polite"
          >
            {file?.name ?? "JPEG, PNG, WebP, HEIC or HEIF"}
          </span>
        </label>
        <button
          type="button"
          onClick={upload}
          disabled={!file || isUploading}
          aria-busy={isUploading}
        >
          {isUploading
            ? activeFollowUp
              ? "Uploading…"
              : "Recognizing…"
            : activeFollowUp
              ? "Upload focused photo"
              : "Recognize food"}
        </button>
        <p className="status" role="status">
          {status}
        </p>
      </section>

      {sentImageUrl && (
        <section>
          <h2>Latest image checked</h2>
          <img
            className="sent-image"
            src={sentImageUrl}
            alt="Clean uploaded image used for recognition"
          />
        </section>
      )}

      {recognition && (
        <section className="results" aria-labelledby="results-heading">
          <div className="results-heading">
            <h2 id="results-heading">Confirm the foods</h2>
            {recognition.items.length > 0 && (
              <span aria-live="polite">
                {confirmedCount} of {recognition.items.length} confirmed
              </span>
            )}
          </div>

          {recognition.no_food_message && (
            <p className="empty-result">{recognition.no_food_message}</p>
          )}

          {certainItems.length > 0 && (
            <section className="result-group" aria-labelledby="certain-foods-heading">
              <div className="result-group-heading">
                <div>
                  <h3 id="certain-foods-heading">Looks clear</h3>
                  <p>Foods the recognition model is confident about.</p>
                </div>
                {unreviewedCertainCount > 0 && (
                  <button type="button" onClick={confirmAllCertain}>
                    Confirm all clear ({unreviewedCertainCount})
                  </button>
                )}
              </div>
              {certainItems.map(({ item, index }) => renderFoodCard(item, index))}
            </section>
          )}

          {uncertainItems.length > 0 && (
            <section
              className="result-group uncertain-group"
              aria-labelledby="uncertain-foods-heading"
            >
              <div className="result-group-heading">
                <div>
                  <h3 id="uncertain-foods-heading">Needs your review</h3>
                  <p>Check each best guess and correct it when needed.</p>
                </div>
              </div>
              {uncertainItems.map(({ item, index }) => renderFoodCard(item, index))}
            </section>
          )}

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

      {expandedImage && (
        <div
          className="image-lightbox-backdrop"
          onClick={(event) => {
            if (event.target === event.currentTarget) closeExpandedImage();
          }}
        >
          <section
            className="image-lightbox"
            role="dialog"
            aria-modal="true"
            aria-labelledby="expanded-image-heading"
          >
            <div className="image-lightbox-header">
              <h2 id="expanded-image-heading">Check {expandedImage.foodName}</h2>
              <button type="button" onClick={closeExpandedImage} autoFocus>
                Close
              </button>
            </div>
            <img
              className="expanded-food-image"
              src={expandedImage.url}
              alt={`Large view of ${expandedImage.foodName} circled in red`}
            />
          </section>
        </div>
      )}
    </main>
  );
}
