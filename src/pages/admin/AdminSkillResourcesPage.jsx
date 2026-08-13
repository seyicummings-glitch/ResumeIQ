import { useState } from 'react'
import { useForm } from 'react-hook-form'
import {
  useAdminSkillResourcesPage,
  useCreateSkillResource,
  useUpdateSkillResource,
  useDeleteSkillResource,
} from '../../hooks/useAdminSkillResources'
import { useDebouncedValue } from '../../hooks/useDebouncedValue'
import { Table, TableHead, Th, TableBody, Td } from '../../components/ui/Table'
import Input from '../../components/ui/Input'
import Button from '../../components/ui/Button'
import Modal from '../../components/ui/Modal'
import ConfirmDialog from '../../components/ui/ConfirmDialog'
import Spinner from '../../components/ui/Spinner'
import ErrorState from '../../components/ui/ErrorState'
import EmptyState from '../../components/ui/EmptyState'
import Pagination from '../../components/ui/Pagination'
import { useToast } from '../../components/ui/Toast'

const PAGE_SIZE = 20

function LinkCell({ url }) {
  if (!url) return <span className="text-text/40">—</span>
  return (
    <a href={url} target="_blank" rel="noopener noreferrer" className="text-accent hover:underline">
      Link
    </a>
  )
}

function ResourceCell({ url, title, subtitle }) {
  if (!url) return <span className="text-text/40">—</span>
  return (
    <div className="flex flex-col">
      <a
        href={url}
        target="_blank"
        rel="noopener noreferrer"
        className="max-w-[14rem] truncate text-accent hover:underline"
        title={title || url}
      >
        {title || 'Link'}
      </a>
      {subtitle ? <span className="text-xs text-text/60">{subtitle}</span> : null}
    </div>
  )
}

export default function AdminSkillResourcesPage() {
  const [page, setPage] = useState(1)
  const [search, setSearch] = useState('')
  const debouncedSearch = useDebouncedValue(search, 300)

  const { data, isLoading, isError, error, refetch } = useAdminSkillResourcesPage({
    page,
    pageSize: PAGE_SIZE,
    search: debouncedSearch,
  })
  const createResource = useCreateSkillResource()
  const updateResource = useUpdateSkillResource()
  const deleteResource = useDeleteSkillResource()
  const { showToast } = useToast()

  const [editingResource, setEditingResource] = useState(null) // null closed, {} for "new"
  const [deletingResource, setDeletingResource] = useState(null)
  const { register, handleSubmit, reset } = useForm()

  function openCreate() {
    setEditingResource({})
    reset({
      skillLabel: '',
      youtubeUrl: '',
      youtubeTitle: '',
      youtubeChannel: '',
      youtubeDuration: '',
      courseUrl: '',
      courseTitle: '',
      courseProvider: '',
      docsUrl: '',
    })
  }

  function openEdit(resource) {
    setEditingResource(resource)
    reset({
      skillLabel: resource.skillLabel,
      youtubeUrl: resource.youtubeUrl || '',
      youtubeTitle: resource.youtubeTitle || '',
      youtubeChannel: resource.youtubeChannel || '',
      youtubeDuration: resource.youtubeDuration || '',
      courseUrl: resource.courseUrl || '',
      courseTitle: resource.courseTitle || '',
      courseProvider: resource.courseProvider || '',
      docsUrl: resource.docsUrl || '',
    })
  }

  async function onSubmitEdit(values) {
    const fields = {
      skillLabel: values.skillLabel,
      youtubeUrl: values.youtubeUrl || null,
      youtubeTitle: values.youtubeTitle || null,
      youtubeChannel: values.youtubeChannel || null,
      youtubeDuration: values.youtubeDuration || null,
      courseUrl: values.courseUrl || null,
      courseTitle: values.courseTitle || null,
      courseProvider: values.courseProvider || null,
      docsUrl: values.docsUrl || null,
    }
    try {
      if (editingResource?.id) {
        await updateResource.mutateAsync({ id: editingResource.id, fields })
        showToast('Skill resource updated.', { tone: 'success' })
      } else {
        await createResource.mutateAsync(fields)
        showToast('Skill resource created.', { tone: 'success' })
      }
      setEditingResource(null)
    } catch (err) {
      showToast(err.message, { tone: 'error' })
    }
  }

  async function confirmDelete() {
    try {
      await deleteResource.mutateAsync(deletingResource.id)
      showToast(`Resources for "${deletingResource.skillLabel}" deleted.`, { tone: 'success' })
      setDeletingResource(null)
    } catch (err) {
      showToast(err.message, { tone: 'error' })
    }
  }

  if (isLoading) {
    return (
      <div className="flex justify-center py-12">
        <Spinner label="Loading skill resources…" />
      </div>
    )
  }

  if (isError) {
    return <ErrorState message={error.message} onRetry={refetch} />
  }

  return (
    <div className="flex flex-col gap-4">
      <div>
        <h2 className="text-lg font-semibold text-text-h">Skill resources</h2>
        <p className="mt-1 text-sm text-text">
          Curated YouTube, course, and documentation links shown on a user's Learning Roadmap for each skill it
          covers. Skills without a curated entry here fall back to generated search links automatically.
        </p>
      </div>

      <div className="flex items-end justify-between gap-3">
        <div className="w-64">
          <Input
            label="Search"
            placeholder="Search by skill name…"
            value={search}
            onChange={(event) => {
              setPage(1)
              setSearch(event.target.value)
            }}
          />
        </div>
        <Button onClick={openCreate}>Add skill resource</Button>
      </div>

      {data.items.length === 0 ? (
        <EmptyState title="No curated skill resources yet" description="Add one for any skill your roadmap covers, or wait for one to matter — every skill already has generated search links as a fallback." />
      ) : (
        <>
          <Table>
            <TableHead>
              <Th>Skill</Th>
              <Th>YouTube</Th>
              <Th>Course</Th>
              <Th>Docs</Th>
              <Th>
                <span className="sr-only">Actions</span>
              </Th>
            </TableHead>
            <TableBody>
              {data.items.map((resource) => (
                <tr key={resource.id}>
                  <Td className="font-medium">{resource.skillLabel}</Td>
                  <Td>
                    <ResourceCell
                      url={resource.youtubeUrl}
                      title={resource.youtubeTitle}
                      subtitle={[resource.youtubeChannel, resource.youtubeDuration].filter(Boolean).join(' · ')}
                    />
                  </Td>
                  <Td>
                    <ResourceCell url={resource.courseUrl} title={resource.courseTitle} subtitle={resource.courseProvider} />
                  </Td>
                  <Td>
                    <LinkCell url={resource.docsUrl} />
                  </Td>
                  <Td>
                    <div className="flex gap-2">
                      <Button variant="secondary" size="sm" onClick={() => openEdit(resource)}>
                        Edit
                      </Button>
                      <Button variant="danger" size="sm" onClick={() => setDeletingResource(resource)}>
                        Delete
                      </Button>
                    </div>
                  </Td>
                </tr>
              ))}
            </TableBody>
          </Table>
          <Pagination page={data.page} pageSize={data.pageSize} total={data.total} onPageChange={setPage} />
        </>
      )}

      <Modal
        isOpen={Boolean(editingResource)}
        onClose={() => setEditingResource(null)}
        title={editingResource?.id ? `Edit ${editingResource.skillLabel}` : 'Add skill resource'}
      >
        <form onSubmit={handleSubmit(onSubmitEdit)} className="flex flex-col gap-4">
          <Input label="Skill name" required {...register('skillLabel', { required: true })} />

          <div className="flex flex-col gap-3 rounded-lg border border-border p-3">
            <p className="text-xs font-semibold uppercase tracking-wide text-text/60">YouTube video card</p>
            <Input label="YouTube tutorial URL" type="url" placeholder="https://youtube.com/…" {...register('youtubeUrl')} />
            <Input label="Video title" placeholder="e.g. React Course - Beginner's Tutorial" {...register('youtubeTitle')} />
            <div className="grid grid-cols-2 gap-3">
              <Input label="Channel name" placeholder="e.g. freeCodeCamp.org" {...register('youtubeChannel')} />
              <Input label="Duration (optional)" placeholder="e.g. 3 Hours" {...register('youtubeDuration')} />
            </div>
          </div>

          <div className="flex flex-col gap-3 rounded-lg border border-border p-3">
            <p className="text-xs font-semibold uppercase tracking-wide text-text/60">Course card</p>
            <Input label="Online course URL" type="url" placeholder="https://…" {...register('courseUrl')} />
            <Input label="Course title" placeholder="e.g. React - The Complete Guide" {...register('courseTitle')} />
            <Input label="Course provider" placeholder="e.g. Udemy, Coursera" {...register('courseProvider')} />
          </div>

          <Input label="Documentation URL (optional)" type="url" placeholder="https://…" {...register('docsUrl')} />
          <div className="flex justify-end gap-2">
            <Button type="button" variant="secondary" onClick={() => setEditingResource(null)}>
              Cancel
            </Button>
            <Button type="submit" isLoading={createResource.isPending || updateResource.isPending}>
              {editingResource?.id ? 'Save changes' : 'Add resource'}
            </Button>
          </div>
        </form>
      </Modal>

      <ConfirmDialog
        isOpen={Boolean(deletingResource)}
        onClose={() => setDeletingResource(null)}
        onConfirm={confirmDelete}
        title="Delete skill resource"
        message={`This removes the curated links for "${deletingResource?.skillLabel || ''}" — the roadmap will fall back to generated search links for this skill.`}
        confirmLabel="Delete"
        isLoading={deleteResource.isPending}
      />
    </div>
  )
}
