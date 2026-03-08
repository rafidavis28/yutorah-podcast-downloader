import { ReactNode } from "react";

type IconProps = {
  className?: string;
};

function IconBase({ className, children }: IconProps & { children: ReactNode }) {
  return (
    <svg
      viewBox="0 0 256 256"
      fill="none"
      stroke="currentColor"
      strokeWidth="18"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
      className={className}
    >
      {children}
    </svg>
  );
}

export function DownloadSimpleIcon({ className }: IconProps) {
  return (
    <IconBase className={className}>
      <path d="M128 40v120" />
      <path d="m80 112 48 48 48-48" />
      <path d="M48 200h160" />
    </IconBase>
  );
}

export function UploadSimpleIcon({ className }: IconProps) {
  return (
    <IconBase className={className}>
      <path d="M128 216V96" />
      <path d="m176 144-48-48-48 48" />
      <path d="M48 56h160" />
    </IconBase>
  );
}

export function PlusCircleIcon({ className }: IconProps) {
  return (
    <IconBase className={className}>
      <circle cx="128" cy="128" r="88" />
      <path d="M128 88v80" />
      <path d="M88 128h80" />
    </IconBase>
  );
}

export function TrashIcon({ className }: IconProps) {
  return (
    <IconBase className={className}>
      <path d="M56 72h144" />
      <path d="M104 72V56h48v16" />
      <path d="m72 72 8 128h96l8-128" />
      <path d="M104 112v64" />
      <path d="M152 112v64" />
    </IconBase>
  );
}

export function LinkSimpleIcon({ className }: IconProps) {
  return (
    <IconBase className={className}>
      <path d="m112 144-24 24a40 40 0 0 1-56-56l24-24" />
      <path d="m144 112 24-24a40 40 0 1 1 56 56l-24 24" />
      <path d="m96 160 64-64" />
    </IconBase>
  );
}

export function SpinnerIcon({ className }: IconProps) {
  return (
    <IconBase className={className}>
      <path d="M216 128a88 88 0 1 1-26-62" />
      <path d="M216 64v48h-48" />
    </IconBase>
  );
}
