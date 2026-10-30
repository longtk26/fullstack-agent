"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { deleteUpload, fetchUploads, uploadImage } from "../api/uploads-api";
import { specKeys } from "../query-keys";

/** The user's uploads and the actions on them (Story 15.4). */
export function useUploads() {
  const queryClient = useQueryClient();
  const list = useQuery({ queryKey: specKeys.uploads(), queryFn: fetchUploads });
  const refresh = () => queryClient.invalidateQueries({ queryKey: specKeys.uploads() });
  const upload = useMutation({ mutationFn: uploadImage, onSuccess: refresh });
  const remove = useMutation({ mutationFn: deleteUpload, onSuccess: refresh });
  return { list, upload, remove };
}
