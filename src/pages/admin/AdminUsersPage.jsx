import { useState } from 'react'
import { Link } from 'react-router-dom'
import { useForm } from 'react-hook-form'
import {
  useAdminUsersPage,
  useUpdateUser,
  useSetUserStatus,
  useDeleteUser,
} from '../../hooks/useAdminData'
import { useDebouncedValue } from '../../hooks/useDebouncedValue'
import { Table, TableHead, Th, TableBody, Td } from '../../components/ui/Table'
import Input from '../../components/ui/Input'
import Select from '../../components/ui/Select'
import Badge from '../../components/ui/Badge'
import Button from '../../components/ui/Button'
import Modal from '../../components/ui/Modal'
import ConfirmDialog from '../../components/ui/ConfirmDialog'
import Spinner from '../../components/ui/Spinner'
import ErrorState from '../../components/ui/ErrorState'
import Pagination from '../../components/ui/Pagination'
import { useToast } from '../../components/ui/Toast'

const PAGE_SIZE = 20

const STATUS_TONE = { active: 'success', deactivated: 'warning', deleted: 'danger' }

function formatDate(value) {
  if (!value) return 'Never'
  return new Intl.DateTimeFormat(undefined, { dateStyle: 'medium' }).format(new Date(value))
}

export default function AdminUsersPage() {
  const [page, setPage] = useState(1)
  const [search, setSearch] = useState('')
  const [roleFilter, setRoleFilter] = useState('all')
  const [statusFilter, setStatusFilter] = useState('all')
  const debouncedSearch = useDebouncedValue(search, 300)

  const { data, isLoading, isError, error, refetch } = useAdminUsersPage({
    page,
    pageSize: PAGE_SIZE,
    search: debouncedSearch,
    role: roleFilter === 'all' ? undefined : roleFilter,
    status: statusFilter === 'all' ? undefined : statusFilter,
  })
  const updateUser = useUpdateUser()
  const setUserStatus = useSetUserStatus()
  const deleteUser = useDeleteUser()
  const { showToast } = useToast()

  const [editingUser, setEditingUser] = useState(null)
  const [deletingUser, setDeletingUser] = useState(null)

  const { register, handleSubmit, reset } = useForm()

  function updateFilter(setter) {
    return (value) => {
      setPage(1)
      setter(value)
    }
  }

  function openEdit(user) {
    setEditingUser(user)
    reset({ fullName: user.fullName, role: user.role, country: user.country || '' })
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

  async function confirmDelete() {
    try {
      await deleteUser.mutateAsync(deletingUser.id)
      showToast(`${deletingUser.email} deleted.`, { tone: 'success' })
      setDeletingUser(null)
    } catch (err) {
      showToast(err.message, { tone: 'error' })
    }
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
          <Input
            label="Search"
            placeholder="Search by name or email…"
            value={search}
            onChange={(event) => updateFilter(setSearch)(event.target.value)}
          />
        </div>
        <div className="w-40">
          <Select label="Role" value={roleFilter} onChange={(event) => updateFilter(setRoleFilter)(event.target.value)}>
            <option value="all">All roles</option>
            <option value="user">User</option>
            <option value="admin">Admin</option>
          </Select>
        </div>
        <div className="w-40">
          <Select label="Status" value={statusFilter} onChange={(event) => updateFilter(setStatusFilter)(event.target.value)}>
            <option value="all">All statuses</option>
            <option value="active">Active</option>
            <option value="deactivated">Deactivated</option>
            <option value="deleted">Deleted</option>
          </Select>
        </div>
      </div>

      <Table>
        <TableHead>
          <Th>Name</Th>
          <Th>Email</Th>
          <Th>Country</Th>
          <Th>Registered</Th>
          <Th>Last login</Th>
          <Th>Status</Th>
          <Th>Activity</Th>
          <Th>
            <span className="sr-only">Actions</span>
          </Th>
        </TableHead>
        <TableBody>
          {data.items.map((user) => (
            <tr key={user.id}>
              <Td>
                <Link to={`/admin/users/${user.id}`} className="font-medium text-accent hover:underline">
                  {user.fullName}
                </Link>
              </Td>
              <Td>{user.email}</Td>
              <Td>{user.country || '—'}</Td>
              <Td>{formatDate(user.createdAt)}</Td>
              <Td>{formatDate(user.lastLoginAt)}</Td>
              <Td>
                <Badge tone={STATUS_TONE[user.status] || 'neutral'}>{user.status}</Badge>
              </Td>
              <Td>{user.totalActivity}</Td>
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
                  <Button variant="danger" size="sm" onClick={() => setDeletingUser(user)}>
                    Delete
                  </Button>
                </div>
              </Td>
            </tr>
          ))}
        </TableBody>
      </Table>

      <Pagination page={data.page} pageSize={data.pageSize} total={data.total} onPageChange={setPage} />

      <Modal isOpen={Boolean(editingUser)} onClose={() => setEditingUser(null)} title={`Edit ${editingUser?.email || ''}`}>
        <form onSubmit={handleSubmit(onSubmitEdit)} className="flex flex-col gap-4">
          <Input label="Full name" {...register('fullName')} />
          <Select label="Role" {...register('role')}>
            <option value="user">User</option>
            <option value="admin">Admin</option>
          </Select>
          <Input label="Country" {...register('country')} />
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

      <ConfirmDialog
        isOpen={Boolean(deletingUser)}
        onClose={() => setDeletingUser(null)}
        onConfirm={confirmDelete}
        title="Delete account"
        message={`This will deactivate ${deletingUser?.email || 'this account'} and block sign-in. Their resumes, analyses, and other activity history are kept.`}
        confirmLabel="Delete account"
        isLoading={deleteUser.isPending}
      />
    </div>
  )
}
