import { useEffect, useRef, useState } from 'react';

// Start capture after the drag threshold so ordinary card-button clicks stay native.
export function useTicketDrag(onMove, disabled) {
  const active = useRef(null);
  const suppressClick = useRef(false);
  const latest = useRef({ onMove, disabled });
  latest.current = { onMove, disabled };
  const [drag, setDrag] = useState(null);
  useEffect(() => {
    const targetAt = event => document.elementFromPoint(event.clientX, event.clientY)?.closest('[data-ticket-column]')?.dataset.ticketColumn || null;
    function clear() {
      const current = active.current;
      active.current = null;
      setDrag(null);
      if (current?.element.hasPointerCapture(current.pointerId)) current.element.releasePointerCapture(current.pointerId);
    }
    function move(event) {
      const current = active.current;
      if (!current || current.pointerId !== event.pointerId) return;
      if (!current.dragging && Math.hypot(event.clientX - current.x, event.clientY - current.y) < 6) return;
      if (!current.dragging) current.element.setPointerCapture(current.pointerId);
      current.dragging = true;
      suppressClick.current = true;
      event.preventDefault();
      setDrag({ ticketId: current.ticket.id, title: current.ticket.title, x: event.clientX, y: event.clientY, over: targetAt(event) });
    }
    function finish(event) {
      const current = active.current;
      if (!current || current.pointerId !== event.pointerId) return;
      const to = current.dragging ? targetAt(event) : null;
      if (current.dragging) event.preventDefault();
      clear();
      if (to && !latest.current.disabled) latest.current.onMove(current.ticket, to, current.ticket.rev);
    }
    const escape = event => { if (event.key === 'Escape') clear(); };
    window.addEventListener('pointermove', move, { passive: false });
    window.addEventListener('pointerup', finish);
    window.addEventListener('pointercancel', clear);
    window.addEventListener('keydown', escape);
    window.addEventListener('blur', clear);
    return () => {
      window.removeEventListener('pointermove', move);
      window.removeEventListener('pointerup', finish);
      window.removeEventListener('pointercancel', clear);
      window.removeEventListener('keydown', escape);
      window.removeEventListener('blur', clear);
      const current = active.current;
      active.current = null;
      if (current?.element.hasPointerCapture(current.pointerId)) current.element.releasePointerCapture(current.pointerId);
    };
  }, []);
  function handlers(ticket) {
    return {
      onPointerDown(event) {
        suppressClick.current = false;
        if (disabled || event.button !== 0 || event.target.closest('select')) return;
        active.current = { ticket: { id: ticket.id, title: ticket.title, state: ticket.state, rev: ticket.rev }, pointerId: event.pointerId, x: event.clientX, y: event.clientY, dragging: false, element: event.currentTarget };
      },
      onClickCapture(event) {
        if (suppressClick.current) { event.preventDefault(); event.stopPropagation(); suppressClick.current = false; }
      },
      onDragStart(event) { event.preventDefault(); },
    };
  }
  return { drag, handlers };
}
