import { useLayoutEffect, useRef, useState, type ReactNode } from "react";
import { createPortal } from "react-dom";
import { Info } from "lucide-react";

type Props = {
  text: string;
};

export default function InfoTip({ text }: Props) {
  const [open, setOpen] = useState(false);
  const btnRef = useRef<HTMLButtonElement>(null);
  const [pos, setPos] = useState({ top: 0, left: 0 });

  useLayoutEffect(() => {
    if (!open || !btnRef.current) return;
    const rect = btnRef.current.getBoundingClientRect();
    const width = 240;
    const left = Math.min(
      Math.max(8, rect.left + rect.width / 2 - width / 2),
      window.innerWidth - width - 8
    );
    setPos({ top: rect.bottom + 6, left });
  }, [open]);

  return (
    <span className="info-tip">
      <button
        ref={btnRef}
        type="button"
        className="info-tip-btn"
        aria-label="More info"
        aria-expanded={open}
        onClick={() => setOpen((v) => !v)}
        onBlur={() => setTimeout(() => setOpen(false), 150)}
      >
        <Info size={13} />
      </button>
      {open &&
        createPortal(
          <span
            className="info-tip-popover"
            role="tooltip"
            style={{ top: pos.top, left: pos.left }}
          >
            {text}
          </span>,
          document.body
        )}
    </span>
  );
}

export function FieldLabel({
  children,
  info,
}: {
  children: ReactNode;
  info?: string;
}) {
  return (
    <span className="label-row">
      {children}
      {info ? <InfoTip text={info} /> : null}
    </span>
  );
}
