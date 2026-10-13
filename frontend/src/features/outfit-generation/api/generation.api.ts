import http from '../../../shared/api/http-client';
import type { IGenerationForm } from '../types';

export interface IGeneration {
  id: string;
  status: string;
}

export interface IOutfitItem {
  id: string;
  name: string;
  brand: string;
  price: number;
  image: string | null;
  marketplace: string;
  url: string;
  recommended_size?: string | null;
  fit?: {
    status: string;
    fit_signal: 'runs_small' | 'true_to_size' | 'runs_large' | null;
    confidence: number | null;
  } | null;
}

export interface IOutfit {
  id: string;
  title: string;
  total_price: number;
  items: IOutfitItem[];
}

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
