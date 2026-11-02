import { isAxiosError } from 'axios';
import http from '../../../shared/api/http-client';
import type { IGeneration, IGenerationForm, IGenerationsPage, IOutfit } from '../types';

export interface IGenerationUsage {
  used: number;
  limit: number;
  remaining: number;
  exhausted: boolean;
}

export async function getGenerationUsage(): Promise<IGenerationUsage> {
  const { data } = await http.get<IGenerationUsage>('/api/v1/generations/usage');
  return data;
}

export function isGenerationLimitError(error: unknown): boolean {
  return isAxiosError(error)
    && error.response?.status === 403
    && error.response?.data?.detail?.code === 'generation_limit_exhausted';
}

export async function createGeneration(values: IGenerationForm): Promise<IGeneration> {
  const { data } = await http.post<IGeneration>('/api/v1/generations', {
    ...values,
    prompt: values.prompt.trim() || null,
  });

  return data;
}

export async function getGenerations(
  page = 1,
  pageSize = 20,
): Promise<IGenerationsPage> {
  const { data } = await http.get<IGenerationsPage>(
    '/api/v1/generations',
    {
      params: {
        page,
        page_size: pageSize,
      },
    },
  );

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
