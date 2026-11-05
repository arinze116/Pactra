interface BrandMarkProps {
  className?: string;
  decorative?: boolean;
}

export function BrandMark({ className = "h-9 w-9", decorative = true }: BrandMarkProps) {
  return (
    <img
      alt={decorative ? "" : "Pactra"}
      aria-hidden={decorative || undefined}
      className={`${className} shrink-0 rounded-[22%] object-cover`}
      height="640"
      src="/brand/pactra-mark.webp"
      width="640"
    />
  );
}
