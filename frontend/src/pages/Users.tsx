import { useQuery } from '@tanstack/react-query';

import { PageHeader } from '../components/shared/PageHeader';
import { api } from '../lib/api';
import type { User } from '../types';

function useUsers() {
  return useQuery({
    queryKey: ['users'],
    queryFn: async () => {
      const resp = await api.get<User[]>('/users');
      return resp.data;
    }
  });
}

export function UsersPage() {
  const { data: users = [], isLoading } = useUsers();

  return (
    <div>
      <PageHeader title="User Management" subtitle="Role assignment and access control visibility" />

      <section className="rounded border border-slate-200 bg-white">
        <header className="border-b border-slate-200 px-4 py-3">
          <h2 className="text-sm font-semibold text-slate-800">Users</h2>
        </header>

        {isLoading ? (
          <p className="p-4 text-sm text-slate-600">Loading users...</p>
        ) : users.length === 0 ? (
          <p className="p-4 text-sm text-slate-600">No users available.</p>
        ) : (
          <div className="overflow-x-auto">
            <table className="min-w-full text-sm">
              <thead className="bg-slate-50 text-left text-slate-600">
                <tr>
                  <th className="px-4 py-3">Name</th>
                  <th className="px-4 py-3">Email</th>
                  <th className="px-4 py-3">Role</th>
                  <th className="px-4 py-3">Active</th>
                </tr>
              </thead>
              <tbody>
                {users.map((user) => (
                  <tr key={user.id} className="border-t border-slate-100">
                    <td className="px-4 py-3 text-slate-800">{user.name}</td>
                    <td className="px-4 py-3 text-slate-700">{user.email}</td>
                    <td className="px-4 py-3 text-slate-700">{user.role}</td>
                    <td className="px-4 py-3 text-slate-700">{user.is_active ? 'Yes' : 'No'}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>
    </div>
  );
}
