"use client";

import { useState, useRef, useCallback } from "react";

/* eslint-disable @typescript-eslint/no-explicit-any */
type SpeechRecognitionType = any;

type IngestMode = "text" | "file" | "audio";

interface IngestPanelProps {
  onIngest: (text: string, source: string) => void;
  isProcessing: boolean;
}

export default function IngestPanel({ onIngest, isProcessing }: IngestPanelProps) {
  const [mode, setMode] = useState<IngestMode>("text");
  const [text, setText] = useState("");
  const [isDragOver, setIsDragOver] = useState(false);
  const [isRecording, setIsRecording] = useState(false);
  const [transcript, setTranscript] = useState("");
  const fileInputRef = useRef<HTMLInputElement>(null);
  const recognitionRef = useRef<SpeechRecognitionType>(null);

  const charCount = text.length;
  const charClass = charCount > 3800 ? "danger" : charCount > 3000 ? "warn" : "";

  function readFile(file: File) {
    // Support text files, JSON, CSV, etc.
    const reader = new FileReader();
    reader.onload = (e) => {
      const content = e.target?.result as string;
      setText(content);
    };
    reader.readAsText(file);
  }

  const handleSubmit = () => {
    const content = mode === "audio" ? transcript : text;
    if (content.trim()) {
      onIngest(content, mode === "audio" ? "voice_input" : mode === "file" ? "file_upload" : "text_input");
      setText("");
      setTranscript("");
    }
  };

  const handleFileDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsDragOver(false);
    const file = e.dataTransfer.files[0];
    if (file) readFile(file);
  }, []);

  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) readFile(file);
  };


  const toggleRecording = () => {
    if (isRecording) {
      recognitionRef.current?.stop();
      setIsRecording(false);
      return;
    }

    const SpeechRecognition = (window as unknown as Record<string, unknown>).SpeechRecognition ||
      (window as unknown as Record<string, unknown>).webkitSpeechRecognition;

    if (!SpeechRecognition) {
      alert("Speech recognition is not supported in this browser. Try Chrome or Edge.");
      return;
    }

    const recognition = new (SpeechRecognition as any)();
    recognition.continuous = true;
    recognition.interimResults = true;
    recognition.lang = "en-US";

    let finalTranscript = "";

    recognition.onresult = (event: any) => {
      let interim = "";
      for (let i = event.resultIndex; i < event.results.length; i++) {
        const result = event.results[i];
        if (result.isFinal) {
          finalTranscript += result[0].transcript + " ";
        } else {
          interim += result[0].transcript;
        }
      }
      setTranscript(finalTranscript + interim);
    };

    recognition.onerror = () => {
      setIsRecording(false);
    };

    recognition.onend = () => {
      setIsRecording(false);
    };

    recognitionRef.current = recognition;
    recognition.start();
    setIsRecording(true);
  };

  const currentContent = mode === "audio" ? transcript : text;

  return (
    <div className="glass-card">
      <div className="card-header">
        <span className="card-title">📥 Ingest Data</span>
      </div>
      <div className="card-body">
        <div className="ingest-panel">
          {/* Mode tabs */}
          <div className="ingest-tabs">
            <button
              className={`ingest-tab ${mode === "text" ? "active" : ""}`}
              onClick={() => setMode("text")}
            >
              ✏️ Text
            </button>
            <button
              className={`ingest-tab ${mode === "file" ? "active" : ""}`}
              onClick={() => setMode("file")}
            >
              📄 File
            </button>
            <button
              className={`ingest-tab ${mode === "audio" ? "active" : ""}`}
              onClick={() => setMode("audio")}
            >
              🎙️ Voice
            </button>
          </div>

          {/* Text mode */}
          {mode === "text" && (
            <div className="textarea-wrap">
              <textarea
                className="ingest-textarea"
                value={text}
                onChange={(e) => setText(e.target.value)}
                placeholder="Paste raw field notes, reports, or intelligence data here...&#10;&#10;Example: FIELD REPORT — Critical water leak detected in Sector 7. Agent K and Operative J responding. Cooling array offline."
                maxLength={4000}
              />
              <span className={`char-count ${charClass}`}>
                {charCount}/4,000
              </span>
            </div>
          )}

          {/* File mode */}
          {mode === "file" && (
            <>
              <div
                className={`drop-zone ${isDragOver ? "dragover" : ""}`}
                onDragOver={(e) => { e.preventDefault(); setIsDragOver(true); }}
                onDragLeave={() => setIsDragOver(false)}
                onDrop={handleFileDrop}
                onClick={() => fileInputRef.current?.click()}
              >
                <div className="drop-zone-icon">📂</div>
                <div className="drop-zone-text">
                  Drop a file here or click to browse
                </div>
                <div className="drop-zone-hint">
                  Supports .txt, .csv, .json, .md — up to 4,000 characters
                </div>
              </div>
              <input
                ref={fileInputRef}
                type="file"
                accept=".txt,.csv,.json,.md,.log"
                onChange={handleFileSelect}
                style={{ display: "none" }}
              />
              {text && (
                <div className="textarea-wrap">
                  <textarea
                    className="ingest-textarea"
                    value={text}
                    onChange={(e) => setText(e.target.value)}
                    style={{ minHeight: "100px" }}
                  />
                  <span className={`char-count ${charClass}`}>
                    {charCount}/4,000
                  </span>
                </div>
              )}
            </>
          )}

          {/* Audio/Voice mode */}
          {mode === "audio" && (
            <>
              <div className="mic-section">
                <button
                  className={`mic-btn ${isRecording ? "recording" : ""}`}
                  onClick={toggleRecording}
                >
                  {isRecording ? "⏹" : "🎙"}
                </button>
                <span className="mic-label">
                  {isRecording ? "Recording... Click to stop" : "Click to start recording"}
                </span>
              </div>
              {transcript && (
                <div className="textarea-wrap">
                  <textarea
                    className="ingest-textarea"
                    value={transcript}
                    onChange={(e) => setTranscript(e.target.value)}
                    style={{ minHeight: "80px" }}
                    placeholder="Transcribed speech will appear here..."
                  />
                </div>
              )}
            </>
          )}

          {/* Submit */}
          <button
            className={`btn-submit ${isProcessing ? "processing" : ""}`}
            onClick={handleSubmit}
            disabled={isProcessing || !currentContent.trim()}
          >
            {isProcessing ? (
              <>
                <span className="spinner" />
                Processing...
              </>
            ) : (
              <>⚡ Extract Intelligence</>
            )}
          </button>
        </div>
      </div>
    </div>
  );
}
