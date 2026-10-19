import http from '../../../shared/api/http-client';
import type { IGeneration, IGenerationForm, IOutfit } from '../types';

export async function createGeneration(values: IGenerationForm): Promise<IGeneration> {
  const { data } = await http.post<IGeneration>('/api/v1/generations', {
    ...values,
    prompt: values.prompt.trim() || null,
  });

  return data;
}

export async function getGeneration(id: string): Promise<IGeneration> {
  const { data } = await http.get<IGeneration>(`/api/v1/generations/${id}`);

  return data;
}

export async function getGenerationOutfits(id: string): Promise<IOutfit[]> {
  const { data } = await http.get<IOutfit[]>(`/api/v1/generations/${id}/outfits`);

  return data;
}
