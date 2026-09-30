import { useRef, useState } from "react";

export default function UploadDocument({
  onUpload,
  uploading,
}) {
  const inputRef = useRef(null);
  const [dragging, setDragging] = useState(false);

  async function handleFile(file) {
    if (!file) {
      return;
    }

    if (file.type !== "application/pdf") {
      alert("Only PDF files are supported.");
      return;
    }

    try {
      await onUpload(file);
    } catch {
      // Hook handles the error.
    }
  }

  function handleInput(event) {
    const file = event.target.files?.[0];

    handleFile(file);

    event.target.value = "";
  }

  function handleDrop(event) {
    event.preventDefault();

    setDragging(false);

    const file = event.dataTransfer.files?.[0];

    handleFile(file);
  }

  return (
    <div
      className={`upload-zone ${
        dragging ? "dragging" : ""
      }`}
      onDragOver={(event) => {
        event.preventDefault();
        setDragging(true);
      }}
      onDragLeave={() => setDragging(false)}
      onDrop={handleDrop}
      onClick={() => inputRef.current?.click()}
    >
      <input
        ref={inputRef}
        type="file"
        accept="application/pdf"
        hidden
        onChange={handleInput}
      />

      {uploading ? (
        <p>Uploading...</p>
      ) : (
        <>
          <p>Drop a PDF here</p>
          <span>or click to browse</span>
        </>
      )}
    </div>
  );
}
