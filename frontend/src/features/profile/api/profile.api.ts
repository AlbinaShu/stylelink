import http from '../../../shared/api/http-client';

export async function updateCurrentUser(name: string): Promise<void> {
  await http.patch('/api/v1/users/current', { name });
}
