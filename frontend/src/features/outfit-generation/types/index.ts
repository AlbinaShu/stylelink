export interface IGenerationForm {
  occasion: string | null;
  style: string | null;
  season: string | null;
  budget: number;
  gender: string | null;
  height: number | null;
  weight: number | null;
  chest: number | null;
  waist: number | null;
  hips: number | null;
  prompt: string;
}

export interface IGenerationOption {
  value: string;
  label: string;
}