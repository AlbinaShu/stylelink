export interface IUser {
  id: string;
  email: string;
  name?: string | null;
}

export interface IProfile {
  id: string;
  user_id: string;
  gender: string;
  height: number;
  weight: number;
  chest: number;
  waist: number;
  hips: number;
}

export type IUpdateProfileRequest = Omit<IProfile, 'id' | 'userId'>;
