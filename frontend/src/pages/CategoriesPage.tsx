import { Link } from 'react-router'

import { ErrorState, Spinner } from '../components/ui'
import { useCategories } from '../lib/queries'

export default function CategoriesPage() {
  const categories = useCategories()
  if (categories.isLoading) return <Spinner />
  if (categories.error) return <ErrorState error={categories.error} onRetry={() => categories.refetch()} />

  return (
    <div className="space-y-7 px-4 pt-4">
      {categories.data?.map((category) => (
        <section key={category.id}>
          <h2 className="mb-3 text-lg font-extrabold">{category.name}</h2>
          <ul className="grid grid-cols-4 gap-x-2.5 gap-y-4 sm:grid-cols-6 lg:grid-cols-8">
            {category.children.map((sub) => (
              <li key={sub.id}>
                <Link to={`/c/${category.slug}?sub=${sub.slug}`} className="group flex flex-col items-center gap-1.5 text-center">
                  <span
                    className="grid aspect-square w-full place-items-center rounded-2xl text-4xl transition group-hover:scale-[1.03]"
                    style={{ backgroundColor: sub.color }}
                    aria-hidden
                  >
                    {sub.emoji}
                  </span>
                  <span className="line-clamp-2 text-[11px] font-semibold leading-tight sm:text-xs">{sub.name}</span>
                </Link>
              </li>
            ))}
          </ul>
        </section>
      ))}
    </div>
  )
}
