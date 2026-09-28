import { useEffect, useState } from 'react';

// Hora atual, atualizada a cada 15 s. Para ver outra fase do dia sem esperar: ?hora=21 no endereço.
export function useRelogio() {
  const [agora, setAgora] = useState(() => new Date());
  useEffect(() => {
    const t = setInterval(() => setAgora(new Date()), 15000);
    return () => clearInterval(t);
  }, []);
  // Sem ?hora= no endereço, vale a hora do PC (Number(null) daria 0 e prenderia o relógio na meia-noite).
  const parametro = new URLSearchParams(window.location.search).get('hora');
  const forcada = parametro === null || parametro.trim() === '' ? NaN : Number(parametro);
  if (Number.isInteger(forcada) && forcada >= 0 && forcada < 24) {
    const d = new Date(agora);
    d.setHours(forcada);
    return d;
  }
  return agora;
}

export function useMovimentoReduzido() {
  const consulta = '(prefers-reduced-motion: reduce)';
  const [reduzido, setReduzido] = useState(() => window.matchMedia(consulta).matches);
  useEffect(() => {
    const mq = window.matchMedia(consulta);
    const mudou = () => setReduzido(mq.matches);
    mq.addEventListener('change', mudou);
    return () => mq.removeEventListener('change', mudou);
  }, []);
  return reduzido;
}
