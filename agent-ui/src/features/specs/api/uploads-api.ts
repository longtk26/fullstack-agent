import { apiClient, proxyUrl } from "@/lib/api-client";

/** A user's image for generated sites (Story 15.4); `source` is what a FrontendSpec asset uses. */
export type TUpload = {
  uploadId: string;
  source: string;
  filename: string;
  mime: string;
  bytes: number;
  width: number | null;
  height: number | null;
  sha256: string;
  origin?: "user" | "photo";
  prompt?: string | null;
  createdAt: string | null;
};

export type TUploadList = { uploads: TUpload[]; usedBytes: number; quotaBytes: number };

export function fetchUploads() {
  return apiClient.get<TUploadList>("/uploads");
}

export function uploadImage(file: File) {
  const form = new FormData();
  form.append("file", file);
  return apiClient.post<TUpload>("/uploads", { form });
}

export function deleteUpload(uploadId: string) {
  return apiClient.delete<void>(`/uploads/${uploadId}`);
}

export function uploadContentUrl(uploadId: string) {
  return proxyUrl(`/uploads/${uploadId}/content`);
}
