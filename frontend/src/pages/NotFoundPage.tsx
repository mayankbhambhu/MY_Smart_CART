import { Link } from 'react-router'

import { Button, EmptyState } from '../components/ui'

export default function NotFoundPage() {
  return (
    <EmptyState
      emoji="🧭"
      title="Page not found"
      body="This aisle doesn't exist. Let's get you back to the store."
      action={
        <Link to="/">
          <Button>Go home</Button>
        </Link>
      }
    />
  )
}
