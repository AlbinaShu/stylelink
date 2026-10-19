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

export type GenerationStatus =
  | 'generating_queries'
  | 'searching_products'
  | 'forming_outfits'
  | 'collecting_fit_data'
  | 'predicting_fit'
  | 'completed'
  | 'failed';

export interface IGeneration {
  id: string;
  status: GenerationStatus;
}

export interface IOutfitItem {
  id: string;
  product_id: string;
  name: string;
  brand: string;
  price: number;
  image: string | null;
  marketplace: string;
  url: string;
  category: string | null;
  available_sizes: string[] | null;
  recommended_size: string | null;
  fit?: {
    fit_signal: string | null;
    confidence: number | null;
  } | null;
}

export interface IOutfit {
  id: string;
  title: string;
  occasion: string | null;
  style: string | null;
  total_price: number;
  items: IOutfitItem[];
}
