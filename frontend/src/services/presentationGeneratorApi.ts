/**
 * Presentation Generator API Client
 */

import { fetchWithAuth, API_BASE_URL } from './api';

export interface PresentationGenRequest {
  topic: string;
  slide_count?: number;
  tone?: string;
  theme?: string;
  target_audience?: string;
}

export interface SlideCardItem {
  title: string;
  description: string;
}

export interface SlideOutline {
  slide_number: number;
  title: string;
  subtitle?: string;
  key_takeaway?: string;
  type: string;
  cards?: SlideCardItem[];
  bullets?: string[];
  speaker_notes?: string;
}

export interface PresentationGenResponse {
  success: boolean;
  message: string;
  output_filename: string;
  download_url: string;
  slides_generated: number;
  theme: string;
  outline: {
    presentation_title: string;
    subtitle?: string;
    topic: string;
    target_audience: string;
    seven_cs_applied?: string[];
    slides: SlideOutline[];
  };
}

export async function generatePresentation(
  payload: PresentationGenRequest
): Promise<PresentationGenResponse> {
  const response = await fetchWithAuth(`${API_BASE_URL}/presentation-generator/generate`, {
    method: 'POST',
    body: JSON.stringify(payload),
  });

  if (!response.ok) {
    const errorData = await response.json().catch(() => ({}));
    throw new Error(errorData.message || 'Failed to generate presentation');
  }

  return response.json();
}

export function getGeneratorDownloadUrl(filename: string): string {
  return `${API_BASE_URL}/presentation-generator/download/${encodeURIComponent(filename)}`;
}
