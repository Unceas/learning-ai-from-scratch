import { useRef, useState } from "react";

export default function UploadDocument({
  onUpload,
  uploading,
}) {
  const inputRef = useRef(null);
  const [dragging, setDragging] = useState(false);

  function validateFile(file) {
    if (!file) return false;

    return (
      file.type === "application/pdf" ||
      file.name.toLowerCase().endsWith(".pdf")
    );
  }

  function handleFile(file) {
    if (!validateFile(file)) {
      return;
    }

    onUpload(file);
  }

  function handleInput(event) {
    handleFile(event.target.files?.[0]);
    event.target.value = "";
  }

  return (
    <div
      className={`upload-zone ${dragging ? "dragging" : ""} ${uploading ? "uploading" : ""}`}
      onDragOver={(event) => {
        event.preventDefault();
        setDragging(true);
      }}
      onDragLeave={() => {
        setDragging(false);
      }}
      onDrop={(event) => {
        event.preventDefault();
        setDragging(false);

        handleFile(event.dataTransfer.files?.[0]);
      }}
      onClick={() => {
        if (!uploading) {
          inputRef.current?.click();
        }
      }}
    >
      <input
        ref={inputRef}
        type="file"
        accept=".pdf,application/pdf"
        hidden
        onChange={handleInput}
      />

      {uploading ? (
        <>
          <strong>Uploading...</strong>
          <span>Preparing document for processing.</span>
        </>
      ) : (
        <>
          <strong>Upload a research document</strong>
          <span>Drag and drop a PDF here, or click to browse.</span>
        </>
      )}
    </div>
  );
}
