/**
 * @param {object} props
 * @param {'primary' | 'secondary' | 'ghost' | 'outline'} [props.variant]
 * @param {'sm' | 'md' | 'lg'} [props.size]
 * @param {boolean} [props.loading]
 * @param {React.ReactNode} props.children
 * @param {string} [props.className]
 */
export function Button({
  variant = 'primary',
  size = 'md',
  loading = false,
  children,
  className = '',
  disabled,
  type = 'button',
  ...rest
}) {
  const base =
    'inline-flex items-center justify-center gap-2 font-medium transition-all duration-200 rounded-lg focus:outline-none focus-visible:ring-2 focus-visible:ring-blue-500/40 focus-visible:ring-offset-2 disabled:pointer-events-none disabled:opacity-50';

  const variants = {
    primary:
      'bg-blue-600 text-white shadow-sm shadow-blue-600/20 hover:bg-blue-700 active:scale-[0.98]',
    secondary: 'bg-slate-900 text-white hover:bg-slate-800 active:scale-[0.98]',
    outline:
      'border border-slate-200 bg-white text-slate-800 hover:border-slate-300 hover:bg-slate-50',
    ghost: 'text-slate-700 hover:bg-slate-100',
  };

  const sizes = {
    sm: 'px-3 py-1.5 text-sm',
    md: 'px-4 py-2.5 text-sm',
    lg: 'px-6 py-3 text-base',
  };

  return (
    <button
      type={type}
      className={`${base} ${variants[variant]} ${sizes[size]} ${className}`}
      disabled={disabled || loading}
      {...rest}
    >
      {loading ? (
        <span
          className="h-4 w-4 shrink-0 animate-spin rounded-full border-2 border-current border-t-transparent opacity-90"
          aria-hidden
        />
      ) : null}
      <span className={loading ? 'opacity-95' : undefined}>{children}</span>
    </button>
  );
}
