import { useEffect, useRef } from 'react';

// <dialog> nativo: foco preso dentro, Esc fecha, clique fora fecha.
export default function Dialogo({ aberto, onFechar, rotulo, className = '', children }) {
  const ref = useRef(null);
  useEffect(() => {
    const d = ref.current;
    if (!d) return;
    if (aberto && !d.open) d.showModal();
    if (!aberto && d.open) d.close();
  }, [aberto]);
  return (
    <dialog
      ref={ref}
      className={className}
      aria-labelledby={rotulo}
      onClose={onFechar}
      onClick={(e) => { if (e.target === ref.current) onFechar(); }}
    >
      {aberto && children}
    </dialog>
  );
}
