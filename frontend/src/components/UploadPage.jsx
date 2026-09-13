import { useState, useRef, useEffect, useCallback } from 'react';

// ==========================================================================
// UPLOAD PAGE
// Lets the officer upload a document image (required) and capture a real-time
// live face photo via webcam (or upload a photo file as fallback).
// ==========================================================================

const ACCEPTED_TYPES = ['image/png', 'image/jpeg', 'image/jpg', 'image/webp'];

function isValidFile(file) {
  return file && ACCEPTED_TYPES.includes(file.type);
}

function UploadPage({ onStartScreening }) {
  const [docFile, setDocFile] = useState(null);
  const [docPreview, setDocPreview] = useState(null);
  const [faceFile, setFaceFile] = useState(null);
  const [facePreview, setFacePreview] = useState(null);
  const [faceSource, setFaceSource] = useState(null); // 'camera' | 'file'
  const [activeTab, setActiveTab] = useState('camera'); // 'camera' | 'file'
  const [error, setError] = useState('');
  const [dragOverDoc, setDragOverDoc] = useState(false);

  // Camera states
  const [isCameraActive, setIsCameraActive] = useState(false);
  const [cameraError, setCameraError] = useState('');

  const docInputRef = useRef(null);
  const faceInputRef = useRef(null);
  const videoRef = useRef(null);
  const streamRef = useRef(null);

  const stopCamera = useCallback(() => {
    if (streamRef.current) {
      streamRef.current.getTracks().forEach((track) => track.stop());
      streamRef.current = null;
    }
    if (videoRef.current) {
      videoRef.current.srcObject = null;
    }
    setIsCameraActive(false);
  }, []);

  // Cleanup camera tracks on unmount
  useEffect(() => {
    return () => {
      stopCamera();
    };
  }, [stopCamera]);

  async function startCamera() {
    setCameraError('');
    setError('');

    if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
      setCameraError('Camera API is not supported in this browser. Please use the Upload File tab.');
      return;
    }

    try {
      const stream = await navigator.mediaDevices.getUserMedia({
        video: {
          width: { ideal: 1280 },
          height: { ideal: 720 },
          facingMode: 'user',
        },
        audio: false,
      });

      streamRef.current = stream;
      setIsCameraActive(true);

      // Connect stream to video element
      if (videoRef.current) {
        videoRef.current.srcObject = stream;
        try {
          await videoRef.current.play();
        } catch (playErr) {
          console.error('Error playing camera stream:', playErr);
        }
      }
    } catch (err) {
      console.error('Camera access error:', err);
      if (err.name === 'NotAllowedError' || err.name === 'PermissionDeniedError') {
        setCameraError('Camera permission was denied. Please allow camera access or switch to file upload.');
      } else if (err.name === 'NotFoundError' || err.name === 'DevicesNotFoundError') {
        setCameraError('No camera found on this device. Please switch to file upload.');
      } else {
        setCameraError(`Unable to start camera: ${err.message || 'Unknown error'}. Try uploading a photo instead.`);
      }
      setIsCameraActive(false);
    }
  }

  function capturePhoto() {
    const video = videoRef.current;
    if (!video || !video.videoWidth) {
      setCameraError('Camera stream is not ready for capture.');
      return;
    }

    const canvas = document.createElement('canvas');
    canvas.width = video.videoWidth;
    canvas.height = video.videoHeight;
    const ctx = canvas.getContext('2d');

    // Draw video frame to canvas
    ctx.drawImage(video, 0, 0, canvas.width, canvas.height);

    // Convert canvas to Blob & create File
    canvas.toBlob((blob) => {
      if (!blob) {
        setCameraError('Failed to capture frame from camera.');
        return;
      }
      const capturedFile = new File([blob], 'live_face_capture.jpg', {
        type: 'image/jpeg',
        lastModified: Date.now(),
      });

      setFaceFile(capturedFile);
      setFacePreview(URL.createObjectURL(blob));
      setFaceSource('camera');
      stopCamera();
    }, 'image/jpeg', 0.92);
  }

  function handleDocFile(file) {
    if (!isValidFile(file)) {
      setError('Please upload a valid image file (PNG, JPG, or WEBP).');
      return;
    }
    setError('');
    setDocFile(file);
    setDocPreview(URL.createObjectURL(file));
  }

  function handleFaceFile(file) {
    if (!isValidFile(file)) {
      setError('Please upload a valid image file (PNG, JPG, or WEBP) for the face photo.');
      return;
    }
    setError('');
    setFaceFile(file);
    setFacePreview(URL.createObjectURL(file));
    setFaceSource('file');
  }

  function handleDocDrop(e) {
    e.preventDefault();
    setDragOverDoc(false);
    const file = e.dataTransfer.files[0];
    if (file) handleDocFile(file);
  }

  function handleStart() {
    if (!docFile) {
      setError('Please upload a document before starting screening.');
      return;
    }
    stopCamera();
    onStartScreening({ docFile, faceFile, docPreview, facePreview });
  }

  return (
    <div className="page-container">
      <div className="page-heading">
        <h1>Document Upload &amp; Verification</h1>
        <p className="text-muted">
          Upload an identity document and capture a live face photo to begin the automated screening pipeline.
        </p>
      </div>

      {/* 1. DOCUMENT UPLOAD */}
      <div className="card">
        <h3 className="card__title">1. Identity Document (required)</h3>

        {!docPreview ? (
          <div
            className={`dropzone ${dragOverDoc ? 'dropzone--active' : ''}`}
            onDragOver={(e) => {
              e.preventDefault();
              setDragOverDoc(true);
            }}
            onDragLeave={() => setDragOverDoc(false)}
            onDrop={handleDocDrop}
          >
            <p className="dropzone__text">Drag and drop a document image here</p>
            <p className="text-muted dropzone__or">or</p>
            <button
              type="button"
              className="btn btn--secondary"
              onClick={() => docInputRef.current.click()}
            >
              Browse File
            </button>
            <input
              ref={docInputRef}
              type="file"
              accept="image/*"
              hidden
              onChange={(e) => {
                if (e.target.files && e.target.files[0]) {
                  handleDocFile(e.target.files[0]);
                }
              }}
            />
          </div>
        ) : (
          <div className="preview-block">
            <img src={docPreview} alt="Document preview" className="preview-image" />
            <div className="preview-actions">
              <span className="text-muted">{docFile.name}</span>
              <button
                className="btn btn--ghost"
                onClick={() => {
                  setDocFile(null);
                  setDocPreview(null);
                }}
              >
                Remove &amp; Replace
              </button>
            </div>
          </div>
        )}
      </div>

      {/* 2. LIVE FACE CAPTURE (WITH REAL CAMERA) */}
      <div className="card">
        <h3 className="card__title">2. Live / Presented Face Photo (Biometric Verification)</h3>
        <p className="text-muted card__subtitle">
          Capture a live face photo via camera or upload an image to match against the document portrait.
        </p>

        {/* Tab selection */}
        {!facePreview && (
          <div className="camera-toggle-tabs">
            <button
              type="button"
              className={`camera-tab-btn ${activeTab === 'camera' ? 'camera-tab-btn--active' : ''}`}
              onClick={() => {
                setActiveTab('camera');
                setCameraError('');
              }}
            >
              📷 Live Camera
            </button>
            <button
              type="button"
              className={`camera-tab-btn ${activeTab === 'file' ? 'camera-tab-btn--active' : ''}`}
              onClick={() => {
                setActiveTab('file');
                stopCamera();
                setCameraError('');
              }}
            >
              📁 Upload Photo File
            </button>
          </div>
        )}

        {/* Display Captured or Selected Face Preview */}
        {facePreview ? (
          <div className="preview-block">
            <img src={facePreview} alt="Face preview" className="preview-image preview-image--face" />
            <div className="preview-actions">
              <span className="captured-badge">
                ✓ {faceSource === 'camera' ? 'Live Camera Captured' : 'File Selected'} ({faceFile?.name})
              </span>
              <div style={{ display: 'flex', gap: '8px' }}>
                <button
                  type="button"
                  className="btn btn--secondary"
                  onClick={() => {
                    setFaceFile(null);
                    setFacePreview(null);
                    setActiveTab('camera');
                    startCamera();
                  }}
                >
                  Retake Photo
                </button>
                <button
                  type="button"
                  className="btn btn--ghost"
                  onClick={() => {
                    setFaceFile(null);
                    setFacePreview(null);
                  }}
                >
                  Remove
                </button>
              </div>
            </div>
          </div>
        ) : activeTab === 'camera' ? (
          /* Live Camera Mode */
          <div>
            {isCameraActive ? (
              <div className="camera-box">
                <video
                  ref={(el) => {
                    videoRef.current = el;
                    if (el && streamRef.current && el.srcObject !== streamRef.current) {
                      el.srcObject = streamRef.current;
                      el.play().catch(() => {});
                    }
                  }}
                  autoPlay
                  playsInline
                  muted
                  className="camera-box__video"
                />
                <div className="camera-guide-overlay" />
                <div className="camera-controls">
                  <button
                    type="button"
                    className="camera-shutter-btn"
                    onClick={capturePhoto}
                  >
                    📸 Capture Photo
                  </button>
                  <button
                    type="button"
                    className="btn btn--secondary"
                    onClick={stopCamera}
                  >
                    Cancel
                  </button>
                </div>
              </div>
            ) : (
              <div className="camera-prompt">
                <div className="camera-prompt__icon">📷</div>
                <p className="camera-prompt__text">
                  Activate your webcam to take a live photo for biometric face matching.
                </p>
                <button
                  type="button"
                  className="btn btn--primary"
                  onClick={startCamera}
                >
                  Open Camera
                </button>
              </div>
            )}

            {cameraError && (
              <div className="alert alert--warning" style={{ marginTop: '12px' }}>
                {cameraError}
              </div>
            )}
          </div>
        ) : (
          /* Upload File Mode */
          <div className="dropzone dropzone--secondary">
            <p className="dropzone__text">Select a face image file from your device</p>
            <button
              type="button"
              className="btn btn--secondary"
              onClick={() => faceInputRef.current.click()}
            >
              Browse File
            </button>
            <input
              ref={faceInputRef}
              type="file"
              accept="image/*"
              hidden
              onChange={(e) => {
                if (e.target.files && e.target.files[0]) {
                  handleFaceFile(e.target.files[0]);
                }
              }}
            />
          </div>
        )}
      </div>

      {error && <div className="alert alert--error">{error}</div>}

      <div className="upload-page__footer">
        <button className="btn btn--primary btn--lg" onClick={handleStart}>
          Start Screening
        </button>
      </div>
    </div>
  );
}

export default UploadPage;