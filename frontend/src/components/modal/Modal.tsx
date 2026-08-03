import type { ReactNode } from "react";
import { useEffect, useId, useRef } from "react";

interface ModalProps {
  open: boolean;
  onClose: () => void;
  title: string;
  children: ReactNode;
  message?: string;
}

export function Modal({ open, onClose, title, children, message }: ModalProps) {
  const id = useId();
  const dialogRef = useRef<HTMLDialogElement>(null);

  const suppressCloseRef = useRef(false);

  useEffect(() => {
    const el = dialogRef.current;
    if (!el) return;

    if (open) {
      suppressCloseRef.current = false;
      el.showModal();
    } else if (el.open) {
      suppressCloseRef.current = true;
      el.close();
    }

    return () => {
      if (el.open) {
        suppressCloseRef.current = true;
        el.close();
      }
    };
  }, [open]);

  useEffect(() => {
    const el = dialogRef.current;
    if (!el) return;

    const handleClose = () => {
      if (suppressCloseRef.current) {
        suppressCloseRef.current = false;
        return;
      }
      onClose();
    };

    el.addEventListener("close", handleClose);
    return () => el.removeEventListener("close", handleClose);
  }, [onClose]);

  return (
    <dialog
      ref={dialogRef}
      className={`modal${open ? " modal--open" : ""}`}
      aria-labelledby={`${id}-title`}
      onClick={(e) => {
        if (e.target === dialogRef.current) {
          onClose();
        }
      }}
      onKeyDown={(e) => {
        if ((e.key === "Enter" || e.key === " ") && e.target === dialogRef.current) {
          onClose();
        }
      }}
    >
      <div className="modal__body">
        <div className="modal__header">
          <h2 className="modal__title" id={`${id}-title`}>
            {title}
          </h2>
          <button type="button" className="modal__close" aria-label="Close" onClick={onClose}>
            &times;
          </button>
        </div>
        {children}
        {message !== undefined && <div className="modal__message">{message}</div>}
      </div>
    </dialog>
  );
}
