import { updateCurrentUser } from '../api/profile.api';

export function useProfile() {
    return {
        updateCurrentUser
    };
}
