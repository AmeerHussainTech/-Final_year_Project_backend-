/**
 * FileUploader Component
 * Reusable file input component for document uploads
 */

import React, { useRef } from 'react';
import './FileUploader.css';

interface FileUploaderProps {
  onFileSelect: (file: File) => void;
  accept?: string;
  disabled?: boolean;
  loading?: boolean;
}

const FileUploader: React.FC<FileUploaderProps> = ({
  onFileSelect,
  accept = '.pdf,.pptx,.doc,.docx,.txt',
  disabled = false,
  loading = false,
}) => {
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleClick = () => {
    if (fileInputRef.current) {
      fileInputRef.current.click();
    }
  };

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) {
      onFileSelect(file);
    }
  };

  return (
    <div className="file-uploader">
      <input
        ref={fileInputRef}
        type="file"
        accept={accept}
        onChange={handleFileChange}
        className="file-input"
      />

      <button
        onClick={handleClick}
        disabled={disabled || loading}
        className="upload-button"
      >
        {loading ? 'Uploading...' : 'Choose File'}
      </button>

      <p className="upload-hint">Supported formats: {accept}</p>
    </div>
  );
};

export default FileUploader;
