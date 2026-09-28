import { marked } from 'marked';
import DOMPurify from 'dompurify';

// Entregas vêm de agentes que leem a web: o HTML gerado passa pelo DOMPurify antes de aparecer.
DOMPurify.addHook('afterSanitizeAttributes', (no) => {
  if (no.tagName === 'A') {
    no.setAttribute('target', '_blank');
    no.setAttribute('rel', 'noopener noreferrer');
  }
});

export default function Markdown({ texto }) {
  const html = DOMPurify.sanitize(marked.parse(texto || '', { gfm: true, breaks: false }));
  return <div className="markdown" dangerouslySetInnerHTML={{ __html: html }} />;
}
