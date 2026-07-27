/** Temporary stand-in so routing/navigation work end-to-end before every page is filled in. Replaced page by page. */
export default function PagePlaceholder({ title }) {
  return (
    <div className="py-12">
      <h1 className="text-2xl font-semibold text-text-h">{title}</h1>
      <p className="mt-2 text-text">This page is under construction.</p>
    </div>
  )
}
