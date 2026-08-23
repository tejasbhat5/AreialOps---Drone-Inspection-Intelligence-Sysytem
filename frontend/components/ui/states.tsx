import Link from "next/link";

export function EmptyState({
  title,
  message,
  action,
}: {
  title: string;
  message: string;
  action?: { href: string; label: string };
}) {
  return (
    <div className="empty-state">
      <span className="empty-mark" aria-hidden="true">
        ◇
      </span>
      <h3>{title}</h3>
      <p>{message}</p>
      {action ? (
        <Link className="button button-secondary" href={action.href}>
          {action.label}
        </Link>
      ) : null}
    </div>
  );
}

export function LoadingState() {
  return (
    <div className="loading-grid" aria-label="Loading content" aria-busy="true">
      {Array.from({ length: 6 }, (_, index) => (
        <div className="skeleton" key={index} />
      ))}
    </div>
  );
}

export function ErrorState({
  title,
  message,
  retry,
}: {
  title: string;
  message: string;
  retry?: () => void;
}) {
  return (
    <div className="empty-state error-state">
      <span className="empty-mark" aria-hidden="true">
        !
      </span>
      <h3>{title}</h3>
      <p>{message}</p>
      {retry ? (
        <button className="button" onClick={retry}>
          Try again
        </button>
      ) : null}
    </div>
  );
}
