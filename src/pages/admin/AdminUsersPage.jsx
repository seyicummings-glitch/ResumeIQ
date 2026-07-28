import { useMemo, useState } from 'react'
import { useForm } from 'react-hook-form'
import { useAdminUsers, useUpdateUser, useSetUserStatus } from '../../hooks/useAdminData'
import { Table, TableHead, Th, TableBody, Td } from '../../components/ui/Table'
import Input from '../../components/ui/Input'
import Select from '../../components/ui/Select'
import Badge from '../../components/ui/Badge'
import Button from '../../components/ui/Button'
import Modal from '../../components/ui/Modal'
import Spinner from '../../components/ui/Spinner'
import ErrorState from '../../components/ui/ErrorState'
import { useToast } from '../../components/ui/Toast'

export default function AdminUsersPage() {
  const { data, isLoading, isError, error, refetch } = useAdminUsers()
  const updateUser = useUpdateUser()
  const setUserStatus = useSetUserStatus()
  const { showToast } = useToast()

  const [search, setSearch] = useState('')
  const [roleFilter, setRoleFilter] = useState('all')
  const [editingUser, setEditingUser] = useState(null)

  const filtered = useMemo(() => {
    if (!data) return []
    return data.filter((user) => {
      const matchesRole = roleFilter === 'all' || user.role === roleFilter
      const matchesSearch =
        !search.trim() ||
        user.email.toLowerCase().includes(search.toLowerCase()) ||
        user.fullName.toLowerCase().includes(search.toLowerCase())
      return matchesRole && matchesSearch
    })
  }, [data, search, roleFilter])

  const {
    register,
    handleSubmit,
    reset,
  } = useForm()

  function openEdit(user) {
    setEditingUser(user)
    reset({ fullName: user.fullName, role: user.role })
  }

  async function onSubmitEdit(values) {
    await updateUser.mutateAsync({ id: editingUser.id, fields: values })
    showToast('User updated.', { tone: 'success' })
    setEditingUser(null)
  }

  async function toggleStatus(user) {
    const nextStatus = user.status === 'active' ? 'deactivated' : 'active'
    await setUserStatus.mutateAsync({ id: user.id, status: nextStatus })
    showToast(`${user.email} ${nextStatus === 'active' ? 'reactivated' : 'deactivated'}.`, { tone: 'success' })
  }

  if (isLoading) {
    return (
      <div className="flex justify-center py-12">
        <Spinner label="Loading users…" />
      </div>
    )
  }

  if (isError) {
    return <ErrorState message={error.message} onRetry={refetch} />
  }

  return (
    <div className="flex flex-col gap-4">
      <div className="flex flex-wrap gap-3">
        <div className="w-64">
          <Input label="Search" placeholder="Search by name or email…" value={search} onChange={(event) => setSearch(event.target.value)} />
        </div>
        <div className="w-40">
          <Select label="Role" value={roleFilter} onChange={(event) => setRoleFilter(event.target.value)}>
            <option value="all">All roles</option>
            <option value="user">User</option>
            <option value="admin">Admin</option>
          </Select>
        </div>
      </div>

      <Table>
        <TableHead>
          <Th>Name</Th>
          <Th>Email</Th>
          <Th>Role</Th>
          <Th>Status</Th>
          <Th>Resumes</Th>
          <Th>Joined</Th>
          <Th>
            <span className="sr-only">Actions</span>
          </Th>
        </TableHead>
        <TableBody>
          {filtered.map((user) => (
            <tr key={user.id}>
              <Td>{user.fullName}</Td>
              <Td>{user.email}</Td>
              <Td>
                <Badge tone={user.role === 'admin' ? 'accent' : 'neutral'}>{user.role}</Badge>
              </Td>
              <Td>
                <Badge tone={user.status === 'active' ? 'success' : 'danger'}>{user.status}</Badge>
              </Td>
              <Td>{user.resumesCount}</Td>
              <Td>{new Intl.DateTimeFormat(undefined, { dateStyle: 'medium' }).format(new Date(user.createdAt))}</Td>
              <Td>
                <div className="flex gap-2">
                  <Button variant="secondary" size="sm" onClick={() => openEdit(user)}>
                    Edit
                  </Button>
                  <Button
                    variant={user.status === 'active' ? 'danger' : 'secondary'}
                    size="sm"
                    onClick={() => toggleStatus(user)}
                    isLoading={setUserStatus.isPending && setUserStatus.variables?.id === user.id}
                  >
                    {user.status === 'active' ? 'Deactivate' : 'Activate'}
                  </Button>
                </div>
              </Td>
            </tr>
          ))}
        </TableBody>
      </Table>

      <Modal isOpen={Boolean(editingUser)} onClose={() => setEditingUser(null)} title={`Edit ${editingUser?.email || ''}`}>
        <form onSubmit={handleSubmit(onSubmitEdit)} className="flex flex-col gap-4">
          <Input label="Full name" {...register('fullName')} />
          <Select label="Role" {...register('role')}>
            <option value="user">User</option>
            <option value="admin">Admin</option>
          </Select>
          <div className="flex justify-end gap-2">
            <Button type="button" variant="secondary" onClick={() => setEditingUser(null)}>
              Cancel
            </Button>
            <Button type="submit" isLoading={updateUser.isPending}>
              Save changes
            </Button>
          </div>
        </form>
      </Modal>
    </div>
  )
}
