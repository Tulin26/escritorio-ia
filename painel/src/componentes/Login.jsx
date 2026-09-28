import { useState } from 'react';
import { spriteDono } from '../sprites.js';

export default function Login({ onEntrar }) {
  const [senha, setSenha] = useState('');
  const [erro, setErro] = useState('');
  const [ocupado, setOcupado] = useState(false);

  async function entrar(e) {
    e.preventDefault();
    if (!senha) return setErro('Digite a senha do painel.');
    setOcupado(true);
    setErro('');
    try {
      await onEntrar(senha);
    } catch (err) {
      setErro(err.message);
      setOcupado(false);
    }
  }

  return (
    <main className="login">
      <form className="login-caixa" onSubmit={entrar}>
        <span className="avatar" role="img" aria-label="Seu avatar" style={{ backgroundImage: `url(${spriteDono()})` }} />
        <h1 className="logo">Escritório de IA</h1>
        <p>Painel online. Só você entra.</p>
        <label htmlFor="senha">Senha do painel</label>
        <input id="senha" type="password" autoComplete="current-password" autoFocus value={senha} onChange={(e) => setSenha(e.target.value)} />
        {erro && <div className="aviso" role="alert">{erro}</div>}
        <button className="btn aprovar" type="submit" disabled={ocupado}>{ocupado ? 'Entrando…' : 'Entrar'}</button>
      </form>
    </main>
  );
}
